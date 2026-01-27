#!/bin/bash

# Script để chạy crawler liên tục với resume capability

echo "🚀 Starting Tiki Listing Crawler"
echo "================================"
echo ""
echo "Configuration:"
echo "  Category ID: ${CATEGORY_ID:-870}"
echo "  Max Pages: ${MAX_PAGES:-unlimited}"
echo "  Resume: ${RESUME:-true}"
echo ""
echo "Press Ctrl+C to stop"
echo "================================"
echo ""

# Run crawler
SERVICE=crawl-listing \
CATEGORY_ID=${CATEGORY_ID:-870} \
MAX_PAGES=${MAX_PAGES:-} \
RESUME=${RESUME:-true} \
docker-compose up app

echo ""
echo "✨ Crawler finished!"
