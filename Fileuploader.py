from tkinter import *
import tkinter as tk
from PIL import ImageDraw, ImageTk
from os import *
import easygui
import io
import sqlite3

root = tk.Tk()
root.geometry("800x700")
root.title("Fileuploader")

def setup_database():
    conn = sqlite3.connect("drawings.db")
    cursor = conn.cursor()
    # Create a table to store image data if it doesn't already exist
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

def Hilfe():
    Hilfe = tk.Tk()
    Hilfe = tk.Toplevel()
    root.withdraw()

menubar = Menu(root,
            background="grey"
            )
root.config(menu=menubar)

# create the file_menu
file_menu = Menu(
    menubar,
    tearoff=0,
    background="grey",
)

# add menu items to the File menu
file_menu.add_command(label='Neu')
file_menu.add_command(label='Öffnen...')
file_menu.add_command(label='Einstellungen')
file_menu.add_separator()

# add Exit menu item
file_menu.add_command(
    label='schließen',
    command=root.destroy
)

# add the File menu to the menubar
menubar.add_cascade(
    label="Datei",
    menu=file_menu
)
# create the Help menu
help_menu = Menu(
    menubar,
    tearoff=0,
    background="grey",
)

help_menu.add_command(label='Max...', command=Hilfe)
help_menu.add_command(label='Über...')

# add the Help menu to the menubar
menubar.add_cascade(
    label="Hilfe",
    menu=help_menu,
)

labelFrame1 = tk.LabelFrame(root,
                            text="Fileuploader",
                            background="lightgreen",
                            width=1920,
                            height=50,)
labelFrame1.pack()

LabelFrame2 = tk.LabelFrame(root,
                            background="orange",
                            width=1900,
                            height=500)
LabelFrame2.pack()

def OpenFilebtn1():
 root = tk.Tk()
 root.withdraw()
 Dateipfad = easygui.fileopenbox()

def btn1Click(Canvas1):
 OpenFilebtn1()

def OpenFilebtn2():
 root = tk.Tk()
 root.withdraw()
 Dateipfad = easygui.filesavebox()

def btn2Click(Canvas1):
 OpenFilebtn2()

label_time = LabelFrame(LabelFrame2, pady= 0, padx= 0, bg='lightgray')
label_time.pack(pady=10, padx=10, expand=TRUE)
btn1 = Button(label_time, text = "Dateien hochladen", command=OpenFilebtn1)
btn1.pack(ipadx=60, padx=20, pady=10)
btn2 = Button(label_time, text = "Dateien runterladen", command=OpenFilebtn2)
btn2.pack(ipadx=60, padx=20, pady=10)

Canvas1 = tk.Canvas(
    root,
    width=400,
    height=400,
)
Canvas1.pack()

labelframe4 = tk.LabelFrame(root,
                            width=1920,
                            height=50,
                            bg="lightgreen",
                            text="""Erstellt durch Max Krebs. 2024""")
labelframe4.pack(padx=0,pady=0)

def retrieve_files_from_db(file_id):
    conn = sqlite3.connect("files.db")
    cursor = conn.cursor()
    cursor.execute("SELECT file FROM files WHERE id=?", (file_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        image_data = result[0]
        image = Image.open(io.BytesIO(image_data))
        return image
    return None

# Example usage to display retrieved image in a new Tkinter window
def display_retrieved_file(file_id):
    image = retrieve_files_from_db(file_id)
    if image:
        window = Toplevel()
        window.title("Retrieved Image")
        tk_image = ImageTk.PhotoImage(image)
        label = Label(window, image=tk_image)
        label.image = tk_image  # Keep a reference
        label.pack()

root.mainloop()