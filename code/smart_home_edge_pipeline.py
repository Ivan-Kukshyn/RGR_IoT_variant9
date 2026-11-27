"""RGR IoT variant 9: smart-home energy monitoring and Edge Computing.

Creates synthetic sensor data, flags missing/outlying readings, cleans data,
stores normalized measurements in SQLite, generates analytics and compares
GZIP/ZLIB/BZIP2 compression. Firebase upload/download is enabled only when
FIREBASE_DATABASE_URL and FIREBASE_CREDENTIALS environment variables are set.
No credentials are stored in this source file.
"""
from __future__ import annotations
import os, json, sqlite3, gzip, zlib, bz2, time, random, base64, hashlib
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "iot_rgr_results")).resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SEED = 9
RNG = np.random.default_rng(SEED)
INTERVAL_MIN = 15

SENSOR_META = {
    "temperature_inside_c": ("temperature", "°C", "living room"),
    "temperature_outside_c": ("temperature", "°C", "outdoors"),
    "illuminance_lux": ("illuminance", "lux", "living room"),
    "power_w": ("energy_monitor", "W", "electrical panel"),
    "motion": ("presence", "bool", "living room"),
}


def generate_raw_data(days: int = 7) -> pd.DataFrame:
    """Generate plausible quarter-hour measurements, then add gaps and outliers."""
    n = days * 24 * 60 // INTERVAL_MIN
    ts = pd.date_range("2026-02-02 00:00:00", periods=n, freq=f"{INTERVAL_MIN}min")
    hour = ts.hour.to_numpy() + ts.minute.to_numpy() / 60.0
    day_idx = np.arange(n) / (24 * 60 / INTERVAL_MIN)
    daylight = np.maximum(0, np.sin(np.pi * (hour - 6) / 12))
    daylight[(hour < 6) | (hour > 18)] = 0
    outside = 7 + 3.5 * np.sin(2 * np.pi * (hour - 8) / 24) + 0.7 * np.sin(2*np.pi*day_idx/7)
    inside = 20.7 + 0.9*np.sin(2*np.pi*(hour-13)/24) + RNG.normal(0, 0.25, n)
    lux = np.maximum(0, daylight * 650 + RNG.normal(0, 24, n))
    # The PIR stream is a sampled presence indicator: higher probability during awake hours.
    p_motion = np.where((hour >= 7) & (hour < 23), 0.23, 0.025)
    p_motion = np.where((hour >= 17) & (hour < 22), 0.38, p_motion)
    motion = RNG.binomial(1, p_motion).astype(float)
    # Load comprises the base household load, a heating load and a conditional lamp load.
    heating = np.where(inside < 20.2, 950.0, np.where(inside < 21.0, 350.0, 0.0))
    lamp = np.where((motion == 1) & (lux < 180), 45.0, 0.0)
    appliances = RNG.gamma(shape=2.0, scale=42.0, size=n)
    power = np.maximum(25, 95 + heating + lamp + appliances + RNG.normal(0, 12, n))
    df = pd.DataFrame({
        "timestamp": ts.astype(str),
        "temperature_inside_c": inside,
        "temperature_outside_c": outside,
        "illuminance_lux": lux,
        "power_w": power,
        "motion": motion,
    })
    # Deliberate data-quality defects to demonstrate Edge cleaning.
    for col in list(SENSOR_META):
        miss = RNG.choice(n, size=max(2, int(n*0.012)), replace=False)
        df.loc[miss, col] = np.nan
    for col, vals in {
        "temperature_inside_c": [88.0, -65.0],
        "temperature_outside_c": [91.0, -78.0],
        "illuminance_lux": [160000.0, -15.0],
        "power_w": [8500.0, -250.0],
    }.items():
        for ix, val in zip(RNG.choice(n, size=2, replace=False), vals):
            df.loc[ix, col] = val
    return df


def clean_data(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Mark missing/out-of-range values and repair numeric series by interpolation."""
    df = raw.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").set_index("timestamp")
    cleaned = pd.DataFrame(index=df.index)
    quality_rows = []
    bounds = {
        "temperature_inside_c": (-5, 50),
        "temperature_outside_c": (-35, 60),
        "illuminance_lux": (0, 100000),
        "power_w": (0, 5000),
        "motion": (0, 1),
    }
    for col, (low, high) in bounds.items():
        series = pd.to_numeric(df[col], errors="coerce").copy()
        outlier = series.notna() & ((series < low) | (series > high))
        missing = series.isna()
        quality_rows.append({
            "sensor": col,
            "raw_missing": int(missing.sum()),
            "outliers": int(outlier.sum()),
            "repaired": int((missing | outlier).sum()),
        })
        series[outlier] = np.nan
        if col == "motion":
            # Do not interpolate presence; carry the latest known state and use 0 at the start.
            fixed = series.ffill().bfill().fillna(0).round().astype(int)
        else:
            fixed = series.interpolate(method="time", limit_direction="both")
            fixed = fixed.fillna(float(series.median()) if series.notna().any() else 0.0)
            fixed = fixed.clip(low, high)
        cleaned[col] = fixed
    cleaned = cleaned.reset_index()
    cleaned["timestamp"] = cleaned["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    quality = pd.DataFrame(quality_rows)
    return cleaned, quality


def store_sqlite(raw: pd.DataFrame, cleaned: pd.DataFrame, quality: pd.DataFrame, db_path: Path) -> None:
    """Create normalized devices/readings tables and insert raw + cleaned values."""
    if db_path.exists(): db_path.unlink()
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript("""
        CREATE TABLE devices (
            device_id INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_key TEXT NOT NULL UNIQUE,
            sensor_type TEXT NOT NULL,
            unit TEXT NOT NULL,
            location TEXT NOT NULL
        );
        CREATE TABLE readings (
            reading_id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            raw_value REAL,
            clean_value REAL NOT NULL,
            quality_flag TEXT NOT NULL,
            FOREIGN KEY(device_id) REFERENCES devices(device_id),
            UNIQUE(device_id, timestamp)
        );
        CREATE INDEX idx_readings_time ON readings(timestamp);
        CREATE INDEX idx_readings_device_time ON readings(device_id, timestamp);
        """)
        for key, (stype, unit, location) in SENSOR_META.items():
            conn.execute("INSERT INTO devices(sensor_key,sensor_type,unit,location) VALUES(?,?,?,?)", (key, stype, unit, location))
        raw_indexed = raw.copy()
        for col in SENSOR_META:
            raw_indexed[col] = pd.to_numeric(raw_indexed[col], errors="coerce")
        for _, row in cleaned.iterrows():
            stamp = row["timestamp"]
            for key, (stype, unit, loc) in SENSOR_META.items():
                rv = raw_indexed.loc[raw_indexed["timestamp"].astype(str) == stamp, key]
                raw_value = float(rv.iloc[0]) if len(rv) and pd.notna(rv.iloc[0]) else None
                clean_value = float(row[key])
                # A value is marked repaired when raw value is missing or outside its valid range.
                low, high = {
                    "temperature_inside_c":(-5,50), "temperature_outside_c":(-35,60),
                    "illuminance_lux":(0,100000), "power_w":(0,5000), "motion":(0,1)
                }[key]
                flag = "missing" if raw_value is None else ("outlier" if raw_value < low or raw_value > high else "valid")
                conn.execute("""INSERT INTO readings(device_id,timestamp,raw_value,clean_value,quality_flag)
                            SELECT device_id, ?, ?, ?, ? FROM devices WHERE sensor_key=?""",
                             (stamp, raw_value, clean_value, flag, key))
        conn.commit()
    finally:
        conn.close()


def plot_results(cleaned: pd.DataFrame, daily: pd.DataFrame, compression: pd.DataFrame) -> None:
    plt.rcParams.update({"font.size": 9, "figure.dpi": 150})
    d = cleaned.copy(); d["timestamp"] = pd.to_datetime(d["timestamp"])
    fig, ax = plt.subplots(figsize=(9, 3.5))
    ax.plot(d["timestamp"], d["temperature_inside_c"], label="Температура всередині, °C", linewidth=1.2)
    ax.plot(d["timestamp"], d["temperature_outside_c"], label="Температура зовні, °C", linewidth=1.0)
    ax.set_title("Температура в розумному будинку (модельні дані)"); ax.set_ylabel("°C"); ax.grid(alpha=.25); ax.legend(ncol=2)
    fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(OUTPUT_DIR/"temperature_timeseries.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 3.4))
    ax.bar(daily["date"], daily["energy_kwh"], color="#4472C4")
    ax.set_title("Добове споживання електроенергії"); ax.set_ylabel("кВт·год"); ax.grid(axis="y", alpha=.25)
    ax.tick_params(axis="x", rotation=25); fig.tight_layout(); fig.savefig(OUTPUT_DIR/"daily_energy.png"); plt.close(fig)

    d["hour"] = d["timestamp"].dt.hour
    motion_by_hour = d.groupby("hour")["motion"].sum()
    fig, ax = plt.subplots(figsize=(8, 3.3))
    ax.bar(motion_by_hour.index, motion_by_hour.values, color="#70AD47")
    ax.set_title("Кількість інтервалів із виявленим рухом за годинами"); ax.set_xlabel("Година доби"); ax.set_ylabel("Інтервали"); ax.set_xticks(range(0,24,2)); ax.grid(axis="y", alpha=.25)
    fig.tight_layout(); fig.savefig(OUTPUT_DIR/"motion_by_hour.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 3.4))
    ax.bar(compression["algorithm"], compression["compressed_bytes"], color=["#4472C4", "#ED7D31", "#70AD47"])
    ax.set_title("Розмір оптимізованого набору після стиснення"); ax.set_ylabel("байти"); ax.grid(axis="y", alpha=.25)
    fig.tight_layout(); fig.savefig(OUTPUT_DIR/"compression_comparison.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.5, 3.4))
    ax.plot(d["timestamp"], d["illuminance_lux"], color="#FFC000", linewidth=1.0)
    ax.axhline(180, linestyle="--", color="#C00000", linewidth=1, label="Поріг керування, 180 lux")
    ax.set_title("Освітленість у приміщенні (модельні дані)"); ax.set_ylabel("lux"); ax.grid(alpha=.25); ax.legend()
    fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(OUTPUT_DIR/"illuminance_timeseries.png"); plt.close(fig)


def try_firebase_upload_download(cleaned: pd.DataFrame, compressed_path: Path) -> dict:
    """Upload the smallest compressed dataset to Firebase and verify its round trip.

    Firebase is activated only when FIREBASE_ENABLED=true. The bzip2-compressed
    JSON dataset is Base64-encoded because Realtime Database stores JSON values.
    The downloaded bytes are decoded, decompressed and compared with the original.
    """
    enabled = os.getenv("FIREBASE_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    if not enabled:
        return {
            "status": "SKIPPED",
            "reason": "FIREBASE_ENABLED is false; local processing completed without cloud sync.",
            "uploaded_rows": 0,
            "downloaded_rows": 0,
        }

    database_url = os.getenv("FIREBASE_DATABASE_URL", "").strip()
    credential_path = os.getenv("FIREBASE_CREDENTIALS", "").strip()
    if not database_url or not credential_path or not Path(credential_path).is_file():
        return {
            "status": "ERROR",
            "reason": "Firebase is enabled but FIREBASE_DATABASE_URL or the service-account JSON file is missing.",
            "uploaded_rows": 0,
            "downloaded_rows": 0,
        }
    if not compressed_path.is_file():
        return {
            "status": "ERROR",
            "reason": f"Compressed dataset not found: {compressed_path}",
            "uploaded_rows": 0,
            "downloaded_rows": 0,
        }

    try:
        import firebase_admin
        from firebase_admin import credentials, db

        original_bytes = compressed_path.with_suffix(".json").read_bytes()
        compressed_bytes = compressed_path.read_bytes()
        digest = hashlib.sha256(original_bytes).hexdigest()
        if bz2.decompress(compressed_bytes) != original_bytes:
            raise ValueError("Local bzip2 integrity check failed before upload")

        try:
            app = firebase_admin.get_app("rgr_variant9")
        except ValueError:
            cred = credentials.Certificate(credential_path)
            app = firebase_admin.initialize_app(cred, {"databaseURL": database_url}, name="rgr_variant9")

        payload = {
            "metadata": {
                "variant": 9,
                "compression": "bzip2",
                "encoding": "base64",
                "rows": int(len(cleaned)),
                "original_bytes": len(original_bytes),
                "compressed_bytes": len(compressed_bytes),
                "sha256_original": digest,
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            },
            "compressed_dataset_base64": base64.b64encode(compressed_bytes).decode("ascii"),
        }

        ref = db.reference("/rgr_iot_variant9/smart_home", app=app)
        ref.set(payload)
        downloaded = ref.get()
        if not isinstance(downloaded, dict):
            raise ValueError("Firebase read-back returned an empty or invalid object")

        downloaded_meta = downloaded.get("metadata", {})
        encoded = downloaded.get("compressed_dataset_base64")
        if not encoded:
            raise ValueError("Firebase read-back did not contain the compressed dataset")

        downloaded_compressed = base64.b64decode(encoded, validate=True)
        restored_bytes = bz2.decompress(downloaded_compressed)
        if hashlib.sha256(restored_bytes).hexdigest() != downloaded_meta.get("sha256_original"):
            raise ValueError("SHA-256 verification failed after Firebase download")
        if restored_bytes != original_bytes:
            raise ValueError("Downloaded dataset differs from the uploaded dataset")

        records = json.loads(restored_bytes.decode("utf-8"))
        downloaded_df = pd.DataFrame(records)
        downloaded_csv = OUTPUT_DIR / "firebase_downloaded_readings.csv"
        downloaded_df.to_csv(downloaded_csv, index=False)
        report = {
            "status": "OK",
            "firebase_path": "/rgr_iot_variant9/smart_home",
            "compression": "bzip2",
            "uploaded_rows": int(len(cleaned)),
            "downloaded_rows": int(len(downloaded_df)),
            "original_bytes": len(original_bytes),
            "compressed_bytes": len(compressed_bytes),
            "sha256_verified": True,
            "downloaded_csv": str(downloaded_csv),
        }
        (OUTPUT_DIR / "firebase_roundtrip_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return report
    except Exception as exc:
        return {
            "status": "ERROR",
            "reason": f"{type(exc).__name__}: {exc}",
            "uploaded_rows": 0,
            "downloaded_rows": 0,
        }


def main() -> None:
    start = time.perf_counter()
    raw = generate_raw_data(days=7)
    raw.to_csv(OUTPUT_DIR/"readings_raw.csv", index=False)
    cleaned, quality = clean_data(raw)
    cleaned.to_csv(OUTPUT_DIR/"readings_clean.csv", index=False)
    quality.to_csv(OUTPUT_DIR/"quality_report.csv", index=False)

    devices = pd.DataFrame([
        {"sensor_key": key, "sensor_type": meta[0], "unit": meta[1], "location": meta[2]}
        for key, meta in SENSOR_META.items()
    ])
    devices.to_csv(OUTPUT_DIR/"devices.csv", index=False)
    store_sqlite(raw, cleaned, quality, OUTPUT_DIR/"smart_home.sqlite3")

    c = cleaned.copy(); c["timestamp"] = pd.to_datetime(c["timestamp"])
    c["date"] = c["timestamp"].dt.strftime("%Y-%m-%d")
    interval_h = INTERVAL_MIN / 60
    daily = c.groupby("date").apply(lambda g: pd.Series({
        "energy_kwh": float((g["power_w"] * interval_h).sum()/1000),
        "mean_inside_temp_c": float(g["temperature_inside_c"].mean()),
        "mean_outside_temp_c": float(g["temperature_outside_c"].mean()),
        "motion_intervals": int(g["motion"].sum()),
        "mean_illuminance_lux": float(g["illuminance_lux"].mean()),
    }), include_groups=False).reset_index()
    daily.to_csv(OUTPUT_DIR/"daily_summary.csv", index=False)

    occupied_lamp_intervals = ((c["motion"] == 1) & (c["illuminance_lux"] < 180)).sum()
    total_intervals = len(c)
    lamp_wh_controlled = occupied_lamp_intervals * interval_h * 45.0
    lamp_wh_baseline = total_intervals * interval_h * 45.0
    saving_pct = 100 * (lamp_wh_baseline - lamp_wh_controlled) / lamp_wh_baseline if lamp_wh_baseline else 0
    total_kwh = float(daily["energy_kwh"].sum())

    compact_json = json.dumps(cleaned.to_dict(orient="records"), separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    (OUTPUT_DIR/"optimized_data.json").write_bytes(compact_json)
    compressors = {
        "gzip": lambda b: gzip.compress(b, compresslevel=9, mtime=0),
        "zlib": lambda b: zlib.compress(b, level=9),
        "bzip2": lambda b: bz2.compress(b, compresslevel=9),
    }
    comp_rows = []
    for name, func in compressors.items():
        t0 = time.perf_counter(); packed = func(compact_json); elapsed = time.perf_counter()-t0
        (OUTPUT_DIR/f"optimized_data.{name}").write_bytes(packed)
        # Check the decompressed payload matches the source.
        unpacked = gzip.decompress(packed) if name == "gzip" else (zlib.decompress(packed) if name == "zlib" else bz2.decompress(packed))
        assert unpacked == compact_json, f"Round-trip error in {name}"
        comp_rows.append({"algorithm":name, "original_bytes":len(compact_json), "compressed_bytes":len(packed),
                          "size_percent":100*len(packed)/len(compact_json), "saved_percent":100*(1-len(packed)/len(compact_json)),
                          "compression_seconds":elapsed})
    compression = pd.DataFrame(comp_rows)
    compression.to_csv(OUTPUT_DIR/"compression_report.csv", index=False)

    plot_results(cleaned, daily, compression)
    firebase_result = try_firebase_upload_download(cleaned, OUTPUT_DIR/"optimized_data.bzip2")
    summary = {
        "variant": 9,
        "description": "Smart-home energy monitoring and optimization (synthetic telemetry)",
        "rows": int(len(cleaned)),
        "sampling_interval_minutes": INTERVAL_MIN,
        "days": 7,
        "total_energy_kwh_estimate": round(total_kwh, 3),
        "mean_inside_temperature_c": round(float(cleaned["temperature_inside_c"].mean()), 2),
        "mean_outside_temperature_c": round(float(cleaned["temperature_outside_c"].mean()), 2),
        "motion_intervals": int(cleaned["motion"].sum()),
        "motion_hours_estimate": round(float(cleaned["motion"].sum()*interval_h), 2),
        "missing_and_outlier_summary": quality.to_dict(orient="records"),
        "lighting_control_example": {
            "baseline_assumption": "45 W lamp is on during all sample intervals",
            "controlled_assumption": "45 W lamp is on only when motion=1 and illuminance<180 lux",
            "baseline_lighting_kwh": round(lamp_wh_baseline/1000, 3),
            "estimated_controlled_lighting_kwh": round(lamp_wh_controlled/1000, 3),
            "estimated_saving_percent": round(float(saving_pct), 2),
            "note": "Illustrative model comparison, not a measured or guaranteed household saving."
        },
        "compression": comp_rows,
        "firebase": firebase_result,
        "local_pipeline_seconds": round(time.perf_counter()-start, 3),
    }
    (OUTPUT_DIR/"summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    log_lines = [
        "RGR IoT variant 9 — local pipeline", f"Timestamp: {datetime.now().isoformat(timespec='seconds')}",
        f"Rows (15-min): {len(cleaned)}", f"SQLite: {OUTPUT_DIR/'smart_home.sqlite3'}",
        f"Estimated weekly energy: {total_kwh:.3f} kWh", f"Observed motion intervals: {int(cleaned['motion'].sum())}",
        f"Lighting saving illustration: {saving_pct:.2f}%", "Compression:",
    ]
    for row in comp_rows: log_lines.append(f"  {row['algorithm']}: {row['original_bytes']} -> {row['compressed_bytes']} bytes ({row['saved_percent']:.2f}% saved)")
    log_lines += [f"Firebase status: {firebase_result['status']}", str(firebase_result.get("reason", "")), f"Total local runtime: {summary['local_pipeline_seconds']} s"]
    (OUTPUT_DIR/"run_log.txt").write_text("\n".join(x for x in log_lines if x is not None), encoding="utf-8")
    print("\n".join(x for x in log_lines if x is not None))
    print(f"\nAll outputs saved to: {OUTPUT_DIR}")
    if os.getenv("FIREBASE_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"} and firebase_result["status"] != "OK":
        raise SystemExit("Firebase sync was requested but did not complete successfully. See summary.json and run_log.txt.")

if __name__ == "__main__":
    main()
