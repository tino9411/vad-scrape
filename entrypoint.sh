#!/bin/bash
set -e

# Print working directory and list files for debugging
echo "Current directory: $(pwd)"
echo "Files in current directory:"
ls -la

# Execute the main script
python app.py