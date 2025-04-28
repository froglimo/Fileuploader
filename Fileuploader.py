
import tkinter as tk
from tkinter import Menu, LabelFrame, Button, Label, Toplevel, filedialog, messagebox, BOTTOM, TRUE
from PIL import Image, ImageTk
import sqlite3
import io
import os
from tkinter import Menu, LabelFrame, Button, Label, Toplevel, filedialog, messagebox, BOTTOM, TRUE, Listbox, Scrollbar, END
from urllib.request import urlopen

def resource_path(filename):
    return os.path.join(os.path.dirname(__file__), filename)

root = tk.Tk()
root.geometry("800x800")
root.title("Fileuploader")

def setup_database():
    conn = sqlite3.connect(resource_path("drawings.db"))
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY,
            image BLOB
        )
    ''')
    conn.commit()
    return conn

def save_image_to_db(image_data):
    conn = setup_database()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO images (image) VALUES (?)", (image_data,))
    conn.commit()
    conn.close()

def updates():
    if isinstance(menubar, Menu):
        try:
            response = urlopen("https://github.com")
            print("Update check successful!")
            return response
        except Exception as e:
            print(f"Error opening URL: {e}")
            return None
    else:
        print("menubar is not a Menu instance.")
        return None

def Hilfe():
    hilfe_win = Toplevel(root)
    hilfe_win.title("Hilfe")
    Label(
        hilfe_win,
        text="Dieses Programm ist mein erstes richtiges Programm.\nEs wurde zu Übungszwecken erstellt",
        padx=10,
        pady=10,
        width=40,
        height=5,
    ).pack()

def Über():
    ueber_win = Toplevel(root)
    ueber_win.title("Über")
    Label(
        ueber_win,
        text="Fileuploader\nErstellt durch Max Krebs. 2024",
        padx=10,
        pady=10,
        width=40,
        height=2,
    ).pack()
    
def new_window():
    """Create a new program window instance"""
    new_win = Toplevel(root)
    new_win.title("Neues Fenster")
    new_win.geometry("600x600")
    Label(new_win, 
          text="Neues Fenster", 
          font=("Arial", 14), 
          pady=20
         ).pack()
    Button(new_win,
           text="Schließen",
           command=new_win.destroy
          ).pack(pady=10)

menubar = Menu(root, background="grey")
root.config(menu=menubar)

file_menu = Menu(menubar, tearoff=0, background="grey")
file_menu.add_command(label='Neu', command=new_window)
file_menu.add_command(label='Öffnen...')
file_menu.add_command(label='Einstellungen')
file_menu.add_separator()
file_menu.add_command(label='schließen', command=root.destroy)
file_menu.add_command(label='Speicheranzeige', command=new_window)
menubar.add_cascade(label="Datei", menu=file_menu)

help_menu = Menu(menubar, tearoff=0, background="grey")
help_menu.add_command(label='Max...', command=Hilfe)
help_menu.add_command(label='Updates', command=updates)
help_menu.add_command(label='Über...', command=Über)
menubar.add_cascade(label="Hilfe", menu=help_menu)

labelFrame1 = LabelFrame(root, text="Fileuploader", background="lightgreen", width=1920, height=50)
labelFrame1.pack(fill="x")

try:
    data = urlopen("https://play-lh.googleusercontent.com/OQEWNsErMUfkv31UL7LNKgCqCunc4rW-L6YUX-EyxGleqKPPo1Y6MxJXWuOoJoBhtGg").read()
    pil_image = Image.open(io.BytesIO(data))
    pil_image.thumbnail((200, 200))
    image = ImageTk.PhotoImage(pil_image)
    tk.Label(root, image=image).pack()
except Exception as e:
    tk.Label(root, text=f"Bild konnte nicht geladen werden: {e}").pack()

labelFrame2 = LabelFrame(root, background="orange", width=1920, height=500)
labelFrame2.pack(pady=30, fill="x")

Canvas1 = tk.Canvas(root, width=1920, height=500, background="lightgrey")
Canvas1.pack()

file_listbox = Listbox(labelFrame2, width=80, height=8)
file_listbox.pack(pady=10, padx=10, side="left")
scrollbar = Scrollbar(labelFrame2, orient="vertical", command=file_listbox.yview)
scrollbar.pack(side="left", fill="y")
file_listbox.config(yscrollcommand=scrollbar.set)
def save_file_to_db(filename, filetype, filedata):
    conn = setup_database()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO files (filename, filetype, filedata) VALUES (?, ?, ?)", (filename, filetype, filedata))
    conn.commit()
    conn.close()

def refresh_file_list():
    file_listbox.delete(0, END)
    conn = setup_database()
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, filetype FROM files ORDER BY id DESC")
    for row in cursor.fetchall():
        file_listbox.insert(END, f"{row[0]}: {row[1]} ({row[2]})")
    conn.close()

def OpenFilebtn1():
    file_path = filedialog.askopenfilename(
        parent=root,
        title="Datei auswählen",
        filetypes=[
            ("PDF files", "*.pdf"),
            ("JPEG files", "*.jpg;*.jpeg"),
            ("ZIP files", "*.zip"),
            ("Word documents", "*.docx"),
            ("All files", "*.*"),
        ]
    )
    if file_path:
        try:
            filename = os.path.basename(file_path)
            filetype = os.path.splitext(filename)[1].lower().replace('.', '')
            with open(file_path, "rb") as f:
                filedata = f.read()
            save_file_to_db(filename, filetype, filedata)
            # Show thumbnail if image, else show label
            if filetype in ['jpg', 'jpeg', 'png', 'gif', 'bmp']:
                img = Image.open(io.BytesIO(filedata))
                img.thumbnail((100, 100))
                img_tk = ImageTk.PhotoImage(img)
                img_label = Label(Canvas1, image=img_tk)
                img_label.image = img_tk
                img_label.pack()
            else:
                lbl = Label(Canvas1, text=f"{filename} ({filetype.upper()})", bg="lightgrey")
                lbl.pack()
            refresh_file_list()
        except Exception as e:
            messagebox.showerror("Fehler", f"Datei konnte nicht geöffnet werden:\n{e}")

def OpenFilebtn2():
    selection = file_listbox.curselection()
    if not selection:
        messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie eine Datei aus der Liste aus.")
        return
    selected_index = selection[0]
    file_id = int(file_listbox.get(selected_index).split(":")[0])
    conn = setup_database()
    cursor = conn.cursor()
    cursor.execute("SELECT filename, filetype, filedata FROM files WHERE id=?", (file_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        filename, filetype, filedata = result
        save_path = filedialog.asksaveasfilename(
            parent=root,
            title="Datei speichern unter",
            initialfile=filename,
            defaultextension=f".{filetype}",
            filetypes=[
                ("PDF files", "*.pdf"),
                ("JPEG files", "*.jpg;*.jpeg"),
                ("ZIP files", "*.zip"),
                ("Word documents", "*.docx"),
                ("All files", "*.*"),
            ]
        )
        if save_path:
            try:
                with open(save_path, "wb") as f:
                    f.write(filedata)
                messagebox.showinfo("Erfolg", "Datei wurde gespeichert.")
            except Exception as e:
                messagebox.showerror("Fehler", f"Beim Speichern ist ein Fehler aufgetreten:\n{e}")
    else:
        messagebox.showwarning("Keine Datei", "Keine gespeicherte Datei gefunden.")


label_time = LabelFrame(labelFrame2, pady=0, padx=0, bg='lightgray')
label_time.pack(pady=10, padx=10, expand=TRUE)
btn1 = Button(label_time, text="Dateien hochladen", command=OpenFilebtn1)
btn1.pack(ipadx=60, padx=20, pady=10)
btn2 = Button(label_time, text="Dateien runterladen", command=OpenFilebtn2)
btn2.pack(ipadx=60, padx=20, pady=10)

labelframe4 = LabelFrame(root, width=1920, height=50, bg="lightgreen", text="Erstellt durch Max Krebs. 2024")
labelframe4.pack(side=BOTTOM, fill="x")

root.mainloop()