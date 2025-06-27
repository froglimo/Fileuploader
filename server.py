import os
from flask import Flask, request, render_template, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Where to store uploaded files (will recreate folder structure)
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploaded_folders")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

@app.route("/")
def index():
    return "Welcome—use /upload_folder to upload a folder."

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

if __name__ == "__main__":
    # debug=True for dev only
    app.run(host="127.0.0.1", port=5001)