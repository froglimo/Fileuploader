#!/usr/bin/env python3
import hashlib
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable

from flask import (
    Flask, request, redirect, url_for, render_template_string,
    send_file, abort, flash, jsonify
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
  <title>Fileuploader WebUI</title>
  <style>
    body { margin: 0; }
    header { padding: 8px 16px; border-bottom: 1px solid #1f2227; }
    main { max-width: 1100px; margin: 0 auto; padding: 16px; }
    .muted { color: #a0a7b4; font-size: 0.9rem; }
    .card { background: #0f1216; border: 1px solid #1f2227; border-radius: 10px; padding: 16px; }
    .table-wrap { overflow-x: auto; border: 1px solid #1f2227; border-radius: 8px; }
    table { width: 100%; border-collapse: separate; border-spacing: 0; }
    thead th { position: sticky; top: 0; z-index: 1; background: #0f1216; text-align: left; font-weight: 600; border-bottom: 1px solid #1f2227; }
    th, td { padding: 10px 12px; vertical-align: middle; }
    tbody tr { border-bottom: 1px solid #1a1d23; }
    tbody tr:hover { background: #12161a; }
    td.num { text-align: right; white-space: nowrap; }
    td.filename { max-width: 420px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    td.nowrap { white-space: nowrap; }
    .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; }
    .pill { display: inline-block; background: rgba(0,255,0,0.1); color: #9eff9e; border: 1px solid rgba(0,255,0,0.25); padding: 2px 8px; border-radius: 9999px; font-size: 12px; }
    a { color: #7cc7ff; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .inline { display: inline; }
    td.actions a { margin-right: 8px; }
    td.actions form.inline { margin-left: 4px; }
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
    <h2>Upload files</h2>
    <form class="row" action="{{ url_for('upload') }}" method="post" enctype="multipart/form-data">
        <input type="file" name="files" multiple required>
        <button type="submit">Upload</button>
    </form>
    <p class="muted" style="margin-top:8px;">
        Allowed: images, documents, archives · Max request: {{ max_size_mb }} MB
    </p>
    </div>

    <div class="card" style="margin-top:16px;">
    <h2>Stored files ({{ files|length }})</h2>
    {% if files %}
    <div class="table-wrap">
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
          <td class="num">{{ f.id }}</td>
          <td class="filename" title="{{ f.original_filename }}">{{ f.original_filename }}</td>
          <td><span class="pill">{{ f.content_type or "n/a" }}</span></td>
          <td class="num">{{ "{:,}".format(f.size_bytes) }} B</td>
          <td class="mono muted" title="{{ f.sha256 }}">{{ f.sha256[:16] }}…</td>
          <td class="muted nowrap">{{ f.uploaded_at }}</td>
          <td class="actions">
            <a href="{{ url_for('download_file', file_id=f.id) }}">Download</a>
            <form class="inline" action="{{ url_for('delete_file', file_id=f.id) }}" method="post" onsubmit="return confirm('Delete this file?');">
              <button type="submit">Delete</button>
            </form>
          </td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
    </div>
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
# JSON API for desktop client
# --------------------------
@app.route("/api/upload", methods=["POST"])
def api_upload():
    if "files" not in request.files:
        return jsonify(error="No file part in the request."), 400
    files = request.files.getlist("files")
    if not files:
        return jsonify(error="No files selected."), 400

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
            rejected.append((filename or "(unnamed)") + " (empty)")
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

    return jsonify(saved=saved_count, rejected=rejected)

@app.route("/api/files", methods=["GET"])
def api_files():
    conn = get_db()
    rows = conn.execute(
        "SELECT id, original_filename, content_type, size_bytes, sha256, uploaded_at FROM files ORDER BY id DESC"
    ).fetchall()
    conn.close()
    files = [
        {
            "id": r["id"],
            "original_filename": r["original_filename"],
            "content_type": r["content_type"],
            "size_bytes": r["size_bytes"],
            "sha256": r["sha256"],
            "uploaded_at": r["uploaded_at"],
        }
        for r in rows
    ]
    return jsonify(files=files)

# --------------------------
# Main
# --------------------------

def start_server(host: str = "0.0.0.0", port: int = 5000, debug: bool = False):
    """Start the Flask server; suitable for being called from another process/thread."""
    init_db()
    # Avoid reloader when starting from a background thread
    app.run(host=host, port=port, debug=debug, use_reloader=False)

if __name__ == "__main__":
    start_server(host="0.0.0.0", port=5000, debug=True)
