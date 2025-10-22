#!/bin/bash
# Quick start script for elasticsearch-snowpipe

set -e

echo "================================"
echo "Elasticsearch-Snowpipe Setup"
echo "================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ Created .env file"
    echo ""
    echo "⚠️  Please edit .env and configure your Elasticsearch and Snowflake credentials"
    echo ""
    read -p "Press Enter after you've configured .env to continue..."
else
    echo "✓ .env file found"
fi

echo ""
echo "Building Docker image..."
docker build -t elasticsearch-snowpipe .

if [ $? -eq 0 ]; then
    echo "✓ Docker image built successfully"
    echo ""
    echo "Choose an option:"
    echo "1) Run once (single sync and exit)"
    echo "2) Run continuously (daemon mode)"
    echo "3) Exit"
    echo ""
    read -p "Enter choice [1-3]: " choice

    case $choice in
        1)
            echo ""
            echo "Running single sync..."
            docker run --rm --env-file .env elasticsearch-snowpipe --once
            ;;
        2)
            echo ""
            echo "Starting continuous sync in background..."
            docker run -d --name es-snowpipe --env-file .env --restart unless-stopped elasticsearch-snowpipe
            echo "✓ Container started"
            echo ""
            echo "Useful commands:"
            echo "  View logs:    docker logs -f es-snowpipe"
            echo "  Stop:         docker stop es-snowpipe"
            echo "  Remove:       docker rm es-snowpipe"
            ;;
        3)
            echo "Exiting..."
            exit 0
            ;;
        *)
            echo "Invalid choice"
            exit 1
            ;;
    esac
else
    echo "✗ Docker build failed"
    exit 1
fi
