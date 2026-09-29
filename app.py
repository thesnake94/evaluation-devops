import os
import time

from flask import Flask, Response, jsonify, request
import redis
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)


app = Flask(__name__)


REQUEST_COUNT = Counter(
    "http_requests_total",
    "Nombre total de requetes HTTP recues",
    ["endpoint", "code"],
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "Duree de traitement des requetes HTTP en secondes",
    ["endpoint"],
)

DEPLOYED_VERSION = Gauge(
    "app_deployed_version",
    "Version ou SHA actuellement deploye",
    ["version"],
)

APP_VERSION = os.getenv("APP_VERSION", "local")
DEPLOYED_VERSION.labels(version=APP_VERSION).set(1)


def get_redis_client():
    redis_host = os.getenv("REDIS_HOST", "localhost")

    return redis.Redis(
        host=redis_host,
        port=6379,
        decode_responses=True,
    )


@app.before_request
def start_timer():
    request._metrics_start = time.perf_counter()


@app.after_request
def record_metrics(response):
    if request.path == "/metrics":
        return response

    if request.url_rule:
        endpoint = request.url_rule.rule
    else:
        endpoint = "unmatched"

    duration = time.perf_counter() - request._metrics_start

    REQUEST_COUNT.labels(
        endpoint=endpoint,
        code=str(response.status_code),
    ).inc()

    REQUEST_DURATION.labels(
        endpoint=endpoint,
    ).observe(duration)

    return response


@app.route("/")
def index():
    return jsonify(
        {
            "service": "evaluation-devops",
            "message": "Application DevOps ESIEA",
        }
    ), 200


@app.route("/health")
def health():
    return jsonify(
        {
            "status": "ok",
        }
    ), 200


@app.route("/status")
def status():
    return jsonify(
        {
            "service": "evaluation-devops",
            "status": "running",
            "version": APP_VERSION,
        }
    ), 200


@app.route("/visits")
def visits():
    client = get_redis_client()
    visits_count = client.incr("visits")

    return jsonify(
        {
            "visits": visits_count,
        }
    ), 200


@app.route("/simulate-error")
def simulate_error():
    return jsonify(
        {
            "error": "simulated error",
        }
    ), 500


@app.route("/simulate-latency")
def simulate_latency():
    time.sleep(1)

    return jsonify(
        {
            "status": "slow response",
        }
    ), 200


@app.route("/metrics")
def metrics():
    return Response(
        generate_latest(),
        mimetype=CONTENT_TYPE_LATEST,
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
    )
