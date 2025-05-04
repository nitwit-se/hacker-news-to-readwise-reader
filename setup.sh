#!/bin/bash

# Create a virtual environment using uv
uv venv

# Detect shell type
FISH_SHELL=0
if [ -n "$FISH_VERSION" ] || [ "$(basename "$SHELL")" = "fish" ]; then
    FISH_SHELL=1
fi

# Activate the virtual environment based on shell type
if [ $FISH_SHELL -eq 1 ]; then
    source .venv/bin/activate.fish
else
    source .venv/bin/activate
fi

# Install dependencies using uv
uv pip install -e .

# Install development dependencies
uv pip install -e ".[dev]"

# Install Playwright and Chromium for content extraction
echo "Installing Playwright and Chromium for content extraction..."
uv run python -m playwright install chromium

echo "Setup complete! Virtual environment created and dependencies installed."

# Show appropriate activation instructions based on shell
if [ $FISH_SHELL -eq 1 ]; then
    echo "Activate the environment with: source .venv/bin/activate.fish"
else
    echo "Activate the environment with: source .venv/bin/activate"
fi

echo "Run the program with: hn-poll"