#!/bin/bash

# Check if virtual environment exists, create if it doesn't
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements if needed
pip install -r requirements.txt

# Run the API
python api.py

# Keep the terminal open if there's an error
if [ $? -ne 0 ]; then
    read -p "Press Enter to continue..."
fi
