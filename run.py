"""
run.py

Application entry point for the Library Management System.

Reads the FLASK_ENV environment variable to choose the configuration
(development / testing / production). Defaults to 'development'.

Usage:
    python run.py

Environment variables:
    FLASK_ENV   — Target environment. Default: development
    FLASK_HOST  — Host to bind to. Default: 0.0.0.0
    FLASK_PORT  — Port to listen on. Default: 5000
"""

import os
from app import create_app

# Determine which configuration to load
config_name = os.environ.get("FLASK_ENV", "development")

app = create_app(config_name)

if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", 5000))

    print(f"Starting Library Management System in '{config_name}' mode")
    print(f"Listening on http://{host}:{port}")

    app.run(host=host, port=port)
