import os
import io
import zipfile
from typing import List

from flask import (
    Flask,
    request,
    jsonify,
    send_from_directory,
    abort,
)

from werkzeug.utils import secure_filename

app = Flask(__name__)

# Where to store uploaded files (will recreate folder structure)
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploaded_folders")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# ---------- Helper functions -------------------------------------------------
def sanitize_relative_path(rel_path: str) -> str:
    """
    Preserve sub-directories while sanitising each component
    to eliminate '..', empty parts, or dangerous characters.
    """
    rel_path = os.path.normpath(rel_path)
    parts: List[str] = []
    for part in rel_path.split(os.sep):
        if part in ("", ".", ".."):
            # Skip empty / current / parent dir components
            continue
        parts.append(secure_filename(part))
    return os.path.join(*parts) if parts else ""


def safe_join(base_dir: str, *paths: str) -> str:
    """
    Like Flask's safe_join but standalone:
    ensures the final absolute path is still inside base_dir.
    """
    final_path = os.path.abspath(os.path.join(base_dir, *paths))
    if not final_path.startswith(os.path.abspath(base_dir)):
        raise ValueError("Attempted path traversal attack")
    return final_path


# ---------- Routes -----------------------------------------------------------
@app.route("/")
def index():
    return """
        <h2>File/Folder Upload &amp; Download</h2>
        <ul>
            <li><a href='/upload_folder'>Upload Folder</a></li>
            <li><a href='/upload_file'>Upload File</a></li>
            <li><a href='/download_folder'>Download Folder</a></li>
            <li><a href='/download_file'>Download File</a></li>
        </ul>
    """


@app.route("/upload_folder", methods=["GET"])
def upload_folder_form():
    # Inline HTML so we don't depend on a template file
    return """
        <h3>Upload an Entire Folder</h3>
        <form method="post" enctype="multipart/form-data">
            <input type="file" name="files" webkitdirectory directory multiple>
            <button type="submit">Upload</button>
        </form>
        <a href="/">Back</a>
    """


@app.route("/upload_folder", methods=["POST"])
def handle_folder_upload():
    """
    Receives all files from the directory picker.
    Reconstructs relative paths and saves under UPLOAD_FOLDER.
    """
    files = request.files.getlist("files")
    if not files:
        return jsonify(success=False, message="No files received"), 400

    saved = []
    for f in files:
        rel_path = sanitize_relative_path(f.filename)
        if not rel_path:  # Skip anything that sanitised to empty
            continue
        dest_path = safe_join(app.config["UPLOAD_FOLDER"], rel_path)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        f.save(dest_path)
        saved.append(rel_path)

    return jsonify(success=True, files_saved=saved, upload_folder=app.config["UPLOAD_FOLDER"])


@app.route("/upload_file", methods=["GET"])
def upload_file_form():
    return """
        <h3>Upload a Single File</h3>
        <form method="post" enctype="multipart/form-data">
            <input type="file" name="file">
            <button type="submit">Upload</button>
        </form>
        <a href="/">Back</a>
    """


@app.route("/upload_file", methods=["POST"])
def handle_file_upload():
    file = request.files.get("file")
    if not file or file.filename == "":
        return jsonify(success=False, message="No file received"), 400

    filename = secure_filename(file.filename)
    dest_path = safe_join(app.config["UPLOAD_FOLDER"], filename)
    file.save(dest_path)
    return jsonify(success=True, file_saved=filename, upload_folder=app.config["UPLOAD_FOLDER"])


@app.route("/download_file", methods=["GET", "POST"])
def download_file():
    if request.method == "GET":
        files = []
        for root, dirs, filenames in os.walk(app.config["UPLOAD_FOLDER"]):
            for fname in filenames:
                rel_dir = os.path.relpath(root, app.config["UPLOAD_FOLDER"])
                rel_file = os.path.join(rel_dir, fname) if rel_dir != "." else fname
                files.append(rel_file)
        file_options = "".join(f"<option value='{f}'>{f}</option>" for f in files)
        return f"""
            <h3>Download a File</h3>
            <form method="post">
                <select name="filename">{file_options}</select>
                <button type="submit">Download</button>
            </form>
            <a href="/">Back</a>
        """

    # POST
    filename = request.form.get("filename")
    if not filename:
        abort(400)

    safe_path = sanitize_relative_path(filename)
    abs_path = safe_join(app.config["UPLOAD_FOLDER"], safe_path)

    if not os.path.isfile(abs_path):
        abort(404)

    dir_name = os.path.dirname(safe_path)
    base_name = os.path.basename(safe_path)
    return send_from_directory(
        os.path.join(app.config["UPLOAD_FOLDER"], dir_name), base_name, as_attachment=True
    )


@app.route("/download_folder", methods=["GET"])
def download_folder():
    folders = []
    for root, dirs, files in os.walk(app.config["UPLOAD_FOLDER"]):
        for d in dirs:
            rel_dir = os.path.relpath(os.path.join(root, d), app.config["UPLOAD_FOLDER"])
            folders.append(rel_dir)
    folder_options = "".join(f"<option value='{f}'>{f}</option>" for f in folders)
    return f"""
        <h3>Download a Folder (as ZIP)</h3>
        <form method="post" action="/download_folder_zip">
            <select name="folder">{folder_options}</select>
            <button type="submit">Download ZIP</button>
        </form>
        <a href="/">Back</a>
    """


@app.route("/download_folder_zip", methods=["POST"])
def download_folder_zip():
    folder = request.form.get("folder")
    if not folder:
        abort(400)

    safe_folder = sanitize_relative_path(folder)
    abs_folder = safe_join(app.config["UPLOAD_FOLDER"], safe_folder)

    if not os.path.isdir(abs_folder):
        abort(404)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(abs_folder):
            for file in files:
                abs_file = os.path.join(root, file)
                rel_path = os.path.relpath(abs_file, app.config["UPLOAD_FOLDER"])
                zipf.write(abs_file, rel_path)

    zip_buffer.seek(0)
    return app.response_class(
        zip_buffer.getvalue(),
        mimetype="application/zip",
        headers={"Content-Disposition": f"attachment; filename={os.path.basename(abs_folder)}.zip"},
    )


# No app.run() block – run with a WSGI server or:
# export FLASK_APP=server.py ; flask run --debug