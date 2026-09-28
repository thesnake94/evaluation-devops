import os

from flask import Flask, jsonify
import redis


app = Flask(__name__)


def get_redis_client():
    redis_host = os.getenv("REDIS_HOST", "localhost")
    return redis.Redis(
        host=redis_host,
        port=6379,
        decode_responses=True
    )


@app.route("/")
def index():
    return jsonify({
        "service": "evaluation-devops",
        "message": "Application DevOps ESIEA"
    }), 200


@app.route("/health")
def health():
    return jsonify({
        "status": "ok"
    }), 200


@app.route("/status")
def status():
    return jsonify({
        "service": "evaluation-devops",
        "status": "running"
    }), 200


@app.route("/visits")
def visits():
    client = get_redis_client()
    visits_count = client.incr("visits")

    return jsonify({
        "visits": visits_count
    }), 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000
    )
