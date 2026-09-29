#!/usr/bin/env bash

set -euo pipefail

IMAGE_NAME="${1:?Image name is required}"
CURRENT_TAG="${2:?Current tag is required}"
PREVIOUS_TAG="${3:-}"

NETWORK_NAME="evaluation-network"
REDIS_CONTAINER="evaluation-redis"
APP_CONTAINER="evaluation-app"


healthcheck() {
    for attempt in 1 2 3; do
        echo "Healthcheck attempt ${attempt}/3"

        if curl -fsS http://localhost:5000/health > /dev/null; then
            echo "Application is healthy"
            return 0
        fi

        sleep 5
    done

    return 1
}


start_application() {
    local tag="$1"

    docker rm -f "$APP_CONTAINER" > /dev/null 2>&1 || true

    docker run -d \
        --name "$APP_CONTAINER" \
        --network "$NETWORK_NAME" \
        -e REDIS_HOST="$REDIS_CONTAINER" \
        -p 5000:5000 \
        "${IMAGE_NAME}:${tag}"
}


echo "Creating Docker network if necessary"

docker network inspect "$NETWORK_NAME" > /dev/null 2>&1 \
    || docker network create "$NETWORK_NAME"


echo "Starting Redis"

docker rm -f "$REDIS_CONTAINER" > /dev/null 2>&1 || true

docker run -d \
    --name "$REDIS_CONTAINER" \
    --network "$NETWORK_NAME" \
    redis:7-alpine


echo "Waiting for Redis"

REDIS_READY=0

for attempt in 1 2 3 4 5; do
    if docker exec "$REDIS_CONTAINER" redis-cli ping \
        | grep -q "PONG"; then
        REDIS_READY=1
        break
    fi

    sleep 2
done

if [ "$REDIS_READY" -ne 1 ]; then
    echo "Redis failed to start"
    exit 1
fi


echo "Pulling image ${IMAGE_NAME}:${CURRENT_TAG}"

docker pull "${IMAGE_NAME}:${CURRENT_TAG}"


echo "Starting version ${CURRENT_TAG}"

start_application "$CURRENT_TAG"


if healthcheck; then
    echo "Healthcheck successful"

    echo "Running smoke test with Redis"

    curl -fsS http://localhost:5000/visits

    echo
    echo "Deployment successful: ${CURRENT_TAG}"

    docker ps

    exit 0
fi


echo "Deployment healthcheck failed"
echo "Starting rollback"


docker rm -f "$APP_CONTAINER" > /dev/null 2>&1 || true


if [ -z "$PREVIOUS_TAG" ]; then
    echo "No previous SHA available for rollback"
    exit 1
fi


echo "Pulling previous image ${IMAGE_NAME}:${PREVIOUS_TAG}"

if ! docker pull "${IMAGE_NAME}:${PREVIOUS_TAG}"; then
    echo "Previous image is not available in GHCR"
    exit 1
fi


echo "Restarting previous version ${PREVIOUS_TAG}"

start_application "$PREVIOUS_TAG"


if healthcheck; then
    echo "Rollback successful: ${PREVIOUS_TAG}"
else
    echo "Rollback failed"
fi


# Le déploiement initial a échoué :
# même si le rollback fonctionne, le job doit rester rouge.
exit 1
