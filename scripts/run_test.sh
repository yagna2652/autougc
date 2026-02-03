#!/bin/bash
# Run pipeline tests with environment variables loaded from .env

set -e

# Change to project directory
cd "$(dirname "$0")/.."

# Activate virtual environment
source venv/bin/activate

# Load environment variables from .env file
if [ -f .env ]; then
    echo "Loading environment variables from .env..."
    export $(grep -v '^#' .env | grep -v '^$' | xargs)
else
    echo "Warning: .env file not found"
    echo "Copy .env.example to .env and add your API keys"
    exit 1
fi

# Check for required API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "Error: ANTHROPIC_API_KEY not set in .env"
    exit 1
fi

echo "✓ ANTHROPIC_API_KEY loaded"
echo ""

# Run the test with all arguments passed through
python scripts/test_pipeline.py "$@"
