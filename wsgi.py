from Fileuploader import app  # Import the Flask `app` instance directly from Fileuploader.py

# This file is the entrypoint for WSGI servers (e.g., gunicorn, uWSGI).
# Usage example:
#   gunicorn --bind 127.0.0.1:5001 wsgi:app