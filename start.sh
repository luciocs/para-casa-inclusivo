#!/bin/bash

# Activate the virtual environment, if you're using one
# source ./venv/bin/activate  # Uncomment this line if you're using a virtual environment

# Install the Flask application and requeriments
pip3 install Flask
pip3 install -r requirements.txt

# Run the Flask application
python3 -m flask run --host=0.0.0.0 --port=3000
