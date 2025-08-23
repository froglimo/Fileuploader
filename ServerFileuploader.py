#!/usr/bin/env python3
import hashlib
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable

from flask import (
    Flask, request, redirect, url_for, render_template_string,
    send_file, abort, flash
)
from werkzeug.utils import secure_filename
from io import BytesIO

# --------------------------
# Config
# --------------------------
APP_NAME = "Local File Vault"
DATABASE_PATH = Path("uploads.db")
# ~50 MB hard limit per request; adjust as needed
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  

ALLOWED_EXTENSIONS: Iterable[str] = {
    # images
    "jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff",
    # docs
    "pdf", "txt", "md", "rtf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
    # archives
    "zip", "rar", "7z", "tar", "gz", "bz2", "xz", "tar.gz", "tar.bz2", "tar.xz"
}

# --------------------------
# App
# --------------------------
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
# For flash() messages; in localhost use a simple static key
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-not-secure-on-internet")

# --------------------------
# DB helpers
# --------------------------
def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_filename TEXT NOT NULL,
            stored_filename TEXT NOT NULL,
            content_type TEXT,
            size_bytes INTEGER NOT NULL,
            sha256 TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            data BLOB NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def ext_ok(filename: str) -> bool:
    name = filename.lower()
    if "." not in name:
        return False
    # Allow compound extensions like .tar.gz
    for ext in ALLOWED_EXTENSIONS:
        if name.endswith("." + ext):
            return True
    return False

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

# --------------------------
# Routes
# --------------------------
INDEX_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{{ app_name }}</title>
  <style>
    html, body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 0; background:#0b0c10; color:#e8e8e8; }
    header { padding: 24px; border-bottom: 1px solid #222; }
    main { padding: 24px; max-width: 900px; margin: 0 auto; }
    .card { background: #111317; border: 1px solid #1e1f24; border-radius: 12px; padding: 20px; }
    .row { display: flex; gap: 16px; flex-wrap: wrap; align-items: center; }
    input[type=file] { padding: 12px; background:#0f1115; color:#e8e8e8; border:1px dashed #323232; border-radius: 8px; width: 100%; }
    button { padding: 10px 14px; border: 0; border-radius: 8px; background:#2c67ff; color:white; font-weight:600; cursor:pointer; }
    button:disabled { opacity: .6; cursor:not-allowed; }
    table { width: 100%; border-collapse: collapse; margin-top: 18px; }
    th, td { padding: 10px 8px; border-bottom: 1px solid #1f2127; font-size: 14px; word-break: break-all; }
    .muted { color:#b9b9b9; font-size: 12px; }
    .pill { font-size: 12px; padding: 2px 8px; border-radius: 999px; background:#1e2433; display:inline-block; }
    .flash { background:#1a2a1a; border:1px solid #2e4b2e; padding:10px 12px; border-radius:8px; color:#cfe9cf; margin: 12px 0; }
    a { color:#8db1ff; text-decoration: none; }
    a:hover { text-decoration: underline; }
    form.inline { display: inline; }
  </style>
</head>
<body>
  <header>
    <h1 style="margin:0;">{{ app_name }}</h1>
    <div class="muted">Running on localhost · Files stored in SQLite</div>
  </header>

  <main>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        {% for m in messages %}
          <div class="flash">{{ m }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    <div class="card">
      <h2 style="margin-top:0;">Upload files</h2>
      <form class="row" action="{{ url_for('upload') }}" method="post" enctype="multipart/form-data">
        <input type="file" name="files" multiple required>
        <button type="submit">Upload</button>
      </form>
      <p class="muted" style="margin-top:8px;">
        Allowed: images, documents, archives · Max request: {{ max_size_mb }} MB
      </p>
    </div>

    <div class="card" style="margin-top:16px;">
      <h2 style="margin-top:0;">Stored files ({{ files|length }})</h2>
      {% if files %}
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Filename</th>
            <th>Type</th>
            <th>Size</th>
            <th>SHA-256</th>
            <th>Uploaded</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
        {% for f in files %}
          <tr>
            <td>{{ f.id }}</td>
            <td>{{ f.original_filename }}</td>
            <td><span class="pill">{{ f.content_type or "n/a" }}</span></td>
            <td>{{ "{:,}".format(f.size_bytes) }} B</td>
            <td class="muted">{{ f.sha256[:16] }}…</td>
            <td class="muted">{{ f.uploaded_at }}</td>
            <td>
              <a href="{{ url_for('download_file', file_id=f.id) }}">Download</a>
               · 
              <form class="inline" action="{{ url_for('delete_file', file_id=f.id) }}" method="post" onsubmit="return confirm('Delete this file?');">
                <button type="submit">Delete</button>
              </form>
            </td>
          </tr>
        {% endfor %}
        </tbody>
      </table>
      {% else %}
        <div class="muted">Nothing here yet. Upload something.</div>
      {% endif %}
    </div>
  </main>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    conn = get_db()
    rows = conn.execute("SELECT id, original_filename, content_type, size_bytes, sha256, uploaded_at FROM files ORDER BY id DESC").fetchall()
    conn.close()
    return render_template_string(
        INDEX_TEMPLATE,
        app_name=APP_NAME,
        files=rows,
        max_size_mb=app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024),
    )

@app.route("/upload", methods=["POST"])
def upload():
    if "files" not in request.files:
        flash("No file part in the request.")
        return redirect(url_for("index"))
    files = request.files.getlist("files")
    if not files:
        flash("No files selected.")
        return redirect(url_for("index"))

    saved_count = 0
    rejected = []
    conn = get_db()

    for f in files:
        if f.filename == "":
            continue
        filename = secure_filename(f.filename)
        if not filename or not ext_ok(filename):
            rejected.append(f.filename or "(unnamed)")
            continue

        data = f.read()
        if not data:
            rejected.append(filename + " (empty)")
            continue

        digest = sha256_bytes(data)
        stored_name = f"{digest[:12]}_{filename}"
        uploaded_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"

        conn.execute(
            """
            INSERT INTO files (original_filename, stored_filename, content_type, size_bytes, sha256, uploaded_at, data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                filename,
                stored_name,
                f.mimetype,
                len(data),
                digest,
                uploaded_at,
                sqlite3.Binary(data),
            ),
        )
        saved_count += 1

    conn.commit()
    conn.close()

    if saved_count:
        flash(f"Uploaded {saved_count} file(s) successfully.")
    if rejected:
        flash("Rejected (type/empty): " + ", ".join(rejected))
    return redirect(url_for("index"))

@app.route("/files/<int:file_id>/download", methods=["GET"])
def download_file(file_id: int):
    conn = get_db()
    row = conn.execute("SELECT original_filename, content_type, data FROM files WHERE id = ?", (file_id,)).fetchone()
    conn.close()
    if not row:
        abort(404)
    # Stream from memory; for very large files, consider StreamingResponse patterns
    return send_file(
        BytesIO(row["data"]),
        as_attachment=True,
        download_name=row["original_filename"],
        mimetype=row["content_type"] or "application/octet-stream",
        max_age=0,
        etag=False,
        conditional=False,
        last_modified=None
    )

@app.route("/files/<int:file_id>/delete", methods=["POST"])
def delete_file(file_id: int):
    conn = get_db()
    cur = conn.execute("DELETE FROM files WHERE id = ?", (file_id,))
    conn.commit()
    conn.close()
    if cur.rowcount:
        flash(f"Deleted file #{file_id}.")
    else:
        flash(f"File #{file_id} not found.")
    return redirect(url_for("index"))

# --------------------------
# Main
# --------------------------
if __name__ == "__main__":
    init_db()
    # Run on localhost only; visit http://127.0.0.1:5000
    app.run(host="127.0.0.1", port=5000, debug=True)
