"""Verify generated RGR IoT outputs; exits nonzero when a required check fails."""
from __future__ import annotations
import os
import json
import gzip
import zlib
import bz2
import sqlite3
from pathlib import Path
import pandas as pd

output = Path(os.getenv("OUTPUT_DIR", "iot_rgr_results")).resolve()
required = [
    "readings_raw.csv", "readings_clean.csv", "quality_report.csv",
    "daily_summary.csv", "compression_report.csv", "optimized_data.json",
    "optimized_data.gzip", "optimized_data.zlib", "optimized_data.bzip2",
    "smart_home.sqlite3", "summary.json", "temperature_timeseries.png",
    "daily_energy.png", "illuminance_timeseries.png", "motion_by_hour.png",
    "compression_comparison.png",
]
missing = [name for name in required if not (output / name).is_file()]
if missing:
    raise SystemExit(f"FAIL: missing files: {missing}")

summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
if summary.get("rows") != 672:
    raise SystemExit(f"FAIL: expected 672 readings, got {summary.get('rows')}")

raw = pd.read_csv(output / "readings_raw.csv")
clean = pd.read_csv(output / "readings_clean.csv")
if len(raw) != 672 or len(clean) != 672:
    raise SystemExit("FAIL: raw/clean CSV row count is not 672")

with sqlite3.connect(output / "smart_home.sqlite3") as conn:
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    readings_count = conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
    devices_count = conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
if integrity != "ok" or readings_count != 3360 or devices_count != 5:
    raise SystemExit(f"FAIL: SQLite integrity={integrity}, readings={readings_count}, devices={devices_count}")

original = (output / "optimized_data.json").read_bytes()
checks = {
    "gzip": gzip.decompress((output / "optimized_data.gzip").read_bytes()),
    "zlib": zlib.decompress((output / "optimized_data.zlib").read_bytes()),
    "bzip2": bz2.decompress((output / "optimized_data.bzip2").read_bytes()),
}
if any(payload != original for payload in checks.values()):
    raise SystemExit("FAIL: compressed dataset round-trip check failed")

firebase_enabled = os.getenv("FIREBASE_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
if firebase_enabled:
    fb = summary.get("firebase", {})
    fb_csv = output / "firebase_downloaded_readings.csv"
    fb_report = output / "firebase_roundtrip_report.json"
    if fb.get("status") != "OK" or not fb_csv.is_file() or not fb_report.is_file():
        raise SystemExit(f"FAIL: Firebase round-trip was required but not verified: {fb}")
    downloaded = pd.read_csv(fb_csv)
    if len(downloaded) != 672 or fb.get("sha256_verified") is not True:
        raise SystemExit("FAIL: Firebase read-back row count or checksum verification failed")
    print("Firebase round-trip: PASS (672 rows, SHA-256 verified)")
else:
    print("Firebase round-trip: SKIPPED (FIREBASE_ENABLED=false)")

print("PASS: generated files, 672 readings, SQLite (5 devices / 3360 readings), and gzip/zlib/bzip2 round-trips verified")
print(f"Output directory: {output}")
