# ---------- Stage 1 : builder ----------
FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt .

RUN pip install --user --no-cache-dir -r requirements.txt


# ---------- Stage 2 : runtime ----------
FROM python:3.12-slim

WORKDIR /app

RUN useradd --create-home appuser

COPY --from=builder --chown=appuser:appuser \
    /root/.local /home/appuser/.local

COPY --chown=appuser:appuser app.py .

ENV PATH=/home/appuser/.local/bin:$PATH

USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s \
    --timeout=3s \
    --start-period=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

CMD ["python", "app.py"]
