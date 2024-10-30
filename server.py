# server.py
from flask import Flask, request, redirect, send_from_directory, render_template
import os

app = Flask(__name__)

# Speicherort für hochgeladene Dateien
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Route zum Hochladen von Dateien
@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # Prüfen, ob eine Datei hochgeladen wurde
        if 'file' not in request.files:
            return 'Keine Datei ausgewählt'
        file = request.files['file']
        if file.filename == '':
            return 'Keine Datei ausgewählt'
        if file:
            # Datei speichern
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
            return f"Datei {file.filename} hochgeladen!"
    return '''
    <h1>Datei hochladen</h1>
    <form method="post" enctype="multipart/form-data">
      <input type="file" name="file">
      <input type="submit" value="Hochladen">
    </form>
    '''

# Route zum Herunterladen von Dateien
@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)