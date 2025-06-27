import os
from flask import Flask, request, render_template, jsonify, send_from_directory, abort
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Where to store uploaded files (will recreate folder structure)
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploaded_folders")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

@app.route("/")
def index():
    return """
        <h2>File/Folder Upload & Download</h2>
        <ul>
            <li><a href='/upload_folder'>Upload Folder</a></li>
            <li><a href='/upload_file'>Upload File</a></li>
            <li><a href='/download_folder'>Download Folder</a></li>
            <li><a href='/download_file'>Download File</a></li>
        </ul>
    """

@app.route("/upload_folder", methods=["GET"])
def upload_folder_form():
    # Renders the HTML form with webkitdirectory
    return render_template("upload_folder.html")

@app.route("/upload_folder", methods=["POST"])
def handle_folder_upload():
    """
    Receives all files from the directory picker.
    Reconstructs relative paths and saves under UPLOAD_FOLDER.
    """
    files = request.files.getlist("files")
    if not files:
        return jsonify({"success": False, "message": "No files received"}), 400

    saved = []
    for f in files:
        # f.filename may contain subfolders, e.g. "photos/vacation/img1.jpg"
        rel_path = secure_filename(f.filename)
        dest_path = os.path.join(app.config["UPLOAD_FOLDER"], rel_path)
        dest_dir = os.path.dirname(dest_path)
        os.makedirs(dest_dir, exist_ok=True)
        f.save(dest_path)
        saved.append(rel_path)

    return jsonify({
        "success": True,
        "files_saved": saved,
        "upload_folder": app.config["UPLOAD_FOLDER"]
    })

@app.route("/upload_file", methods=["GET"])
def upload_file_form():
    # Simple HTML form for single file upload
    return """
        <h3>Upload a Single File</h3>
        <form method="post" enctype="multipart/form-data" action="/upload_file">
            <input type="file" name="file">
            <input type="submit" value="Upload">
        </form>
        <a href="/">Back</a>
    """

@app.route("/upload_file", methods=["POST"])
def handle_file_upload():
    file = request.files.get("file")
    if not file or file.filename == "":
        return jsonify({"success": False, "message": "No file received"}), 400

    filename = secure_filename(file.filename)
    dest_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(dest_path)
    return jsonify({
        "success": True,
        "file_saved": filename,
        "upload_folder": app.config["UPLOAD_FOLDER"]
    })

@app.route("/download_file", methods=["GET", "POST"])
def download_file():
    if request.method == "GET":
        # List files for download
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
                <input type="submit" value="Download">
            </form>
            <a href="/">Back</a>
        """
    else:
        filename = request.form.get("filename")
        if not filename:
            abort(400)
        safe_path = os.path.normpath(filename)
        abs_path = os.path.join(app.config["UPLOAD_FOLDER"], safe_path)
        if not abs_path.startswith(app.config["UPLOAD_FOLDER"]) or not os.path.isfile(abs_path):
            abort(404)
        dir_name = os.path.dirname(safe_path)
        base_name = os.path.basename(safe_path)
        return send_from_directory(os.path.join(app.config["UPLOAD_FOLDER"], dir_name), base_name, as_attachment=True)

@app.route("/download_folder", methods=["GET"])
def download_folder():
    # List folders for download (as zip)
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
            <input type="submit" value="Download ZIP">
        </form>
        <a href="/">Back</a>
    """

@app.route("/download_folder_zip", methods=["POST"])
def download_folder_zip():
    import io
    import zipfile

    folder = request.form.get("folder")
    if not folder:
        abort(400)
    safe_folder = os.path.normpath(folder)
    abs_folder = os.path.join(app.config["UPLOAD_FOLDER"], safe_folder)
    if not abs_folder.startswith(app.config["UPLOAD_FOLDER"]) or not os.path.isdir(abs_folder):
        abort(404)

    # Create a zip in memory
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
        headers={
            "Content-Disposition": f"attachment; filename={os.path.basename(abs_folder)}.zip"
        }
    )

# No app.run() block here; use a WSGI server to run this app.