FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg \
    OUTPUT_DIR=/app/output

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY code/ ./code/
COPY notebooks/ ./notebooks/
COPY README.md ./README.md
RUN mkdir -p /app/output

CMD ["sh", "-c", "python code/smart_home_edge_pipeline.py && python code/verify_outputs.py"]
