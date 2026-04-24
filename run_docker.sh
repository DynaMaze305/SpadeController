#!/bin/bash

TEST_MODE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --test)
            TEST_MODE=true
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
    shift
done


if [ "$TEST_MODE" = true ]; then
    echo "Cleaning test container…"
    sudo docker rm spadecontroller-test
    sudo docker rmi spadecontroller-test
else
    echo "Cleaning agents container…"
    sudo docker rm spadecontroller-agent
    sudo docker rmi spadecontroller-agent
fi

sudo docker compose build

if [ "$TEST_MODE" = true ]; then
    echo "Launching test containers (for test)"
    sudo docker compose --profile test up
else
    echo "Launching agents normal container"
    sudo docker compose --profile agent up
fi