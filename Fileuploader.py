from tkinter import *
import tkinter as tk
from PIL import *
from os import *
import easygui
import io
import sqlite3

root = tk.Tk()
root.geometry("800x400")
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

help_menu.add_command(label='Max')
help_menu.add_command(label='Über...')

# add the Help menu to the menubar
menubar.add_cascade(
    label="Hilfe",
    menu=help_menu,
)

labelFrame1 = tk.LabelFrame(root,
                            text="Fileuploader",
                            background="lightgreen",
                            width=800,
                            height=50,)
labelFrame1.pack()

LabelFrame2 = tk.LabelFrame(root,
                            background="orange",
                            width=800,
                            height=350)
LabelFrame2.pack()

def OpenFilebtn1():
 root = tk.Tk()
 root.withdraw()
 Dateipfad = easygui.fileopenbox()

def btn1Click(self):
 OpenFilebtn1()

def OpenFilebtn2():
 root = tk.Tk()
 root.withdraw()
 Dateipfad = easygui.filesavebox()

def btn2Click(self):
 OpenFilebtn2()

label_time = LabelFrame(LabelFrame2, pady= 0, padx= 0, bg='lightgray')
label_time.pack()
btn1 = Button(label_time, text = "Dateien hochladen", command=OpenFilebtn1)
btn1.pack(ipadx=60)
btn2 = Button(label_time, text = "Dateien runterladen", command=OpenFilebtn2)
btn2.pack(ipadx=60)

def DragEvent(event):
  
 class DrawingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Drawing Canvas")
        self.canvas = Canvas(root, bg="white", width=400, height=400)
        self.canvas.pack()

        # Initialize Pillow Image and ImageDraw
        self.image = Image.new("RGB", (400, 400), "white")
        self.draw = ImageDraw.Draw(self.image)

        # Bind mouse events for drawing
        self.canvas.bind("<B1-Motion>", self.paint)
        self.last_x, self.last_y = None, None

        # Save button
        save_button = Button(root, text="Save", command=self.save_drawing)
        save_button.pack()

    def paint(self, event):
        x, y = event.x, event.y
        if self.last_x and self.last_y:
            self.canvas.create_line(self.last_x, self.last_y, x, y, fill="black", width=2)
            self.draw.line((self.last_x, self.last_y, x, y), fill="black", width=2)
        self.last_x, self.last_y = x, y

    def reset(self, event):
        self.last_x, self.last_y = None, None

    def save_drawing(self):
        # Save the Pillow image to a binary format (like PNG in memory)
        byte_io = io.BytesIO()
        self.image.save(byte_io, "PNG")
        image_data = byte_io.getvalue()
        save_image_to_db(image_data)
        print("Image saved to database!")

    def run(self):
        self.canvas.bind("<ButtonRelease-1>", self.reset)

root.mainloop()