# client.py
import requests

# Datei hochladen
def upload_file(file_path):
    url = 'http://127.0.0.1:5000/upload'
    files = {'file': open(file_path, 'rb')}
    response = requests.post(url, files=files)
    print(response.text)

# Datei herunterladen
def download_file(file_name):
    url = f'http://127.0.0.1:5000/download/{file_name}'
    response = requests.get(url)
    if response.status_code == 200:
        with open(file_name, 'wb') as f:
            f.write(response.content)
        print(f"Datei {file_name} heruntergeladen!")
    else:
        print(f"Fehler beim Herunterladen der Datei: {response.status_code}")

# Beispiel: Datei hochladen und herunterladen
if __name__ == '__main__':
    file_to_upload = '/upload'  # Pfad zur Datei, die hochgeladen werden soll
    upload_file(file_to_upload)

    file_to_download = '/download'  # Dateiname der herunterzuladenden Datei
    download_file(file_to_download)