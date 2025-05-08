import tkinter as tk
from tkinter import messagebox
from tkinter import TclError
import pandas as pd
import socket
import select
import json
import csv
import subprocess
import rsamodule as rsa

global current_user 
current_user = None
chat_proc = None

# function to show a specific frame
def show_frame(frame, username=None):
    frame.tkraise()
    if frame == select_chat_page and username:
        username_label.config(text=f"Logged in as: {username}")

# function to clear all entries in a page
def clear_all_entries(page):
    for widget in page.winfo_children():
        if isinstance(widget, tk.Entry):
            widget.delete(0, tk.END)
        elif isinstance(widget, tk.Frame):
            clear_all_entries(widget)

# function to add a new account
def add_account(username, password):
    df = pd.read_csv("client_side/localcache.csv")
    if username in df["username"].values:
        messagebox.showinfo("Alert", "Username already exists.")
        show_frame(create_account_page)
        return
    else:
        # server details
        SERVER_IP = "127.0.0.1"
        SERVER_PORT = 5454

        # creating a socket
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((SERVER_IP, SERVER_PORT))

        # generating keys
        n, e, d = rsa.generate_keypair(10)

        # creating a new user
        new_user = {"username": username, "password": password, 
                    "n": n, "e": e}

        data = ("a " + json.dumps(new_user) + "\n").encode()
        client_socket.sendall(data)
        client_socket.close()

        # storing local cache
        pd.DataFrame({"username": [username]}).to_csv(
                "client_side/localcache.csv",
                mode='a',               
                header=False,           
                index=False,            
                quoting=csv.QUOTE_MINIMAL)

        filename = f"client_side/rsakeys/{username}.txt"
        with open(filename, 'w') as f:
            f.write(f"{n}, {e}, {d}")

        messagebox.showinfo("Alert", "Account created successfully.")
        clear_all_entries(create_account_page)
        show_frame(start_page)

# function to login a user
def login_account(username, password, connect_timeout=5.0, response_timeout=5.0):
    SERVER_IP = "127.0.0.1"
    SERVER_PORT = 5454

    # Local cache check
    df = pd.read_csv("client_side/localcache.csv")
    if username not in df["username"].values:
        messagebox.showerror("Login Failed", "Invalid username.")
        show_frame(login_page)
        return False

    # Open non-blocking socket and start connect
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    try:
        sock.connect((SERVER_IP, SERVER_PORT))
    except BlockingIOError:
        pass

    # Wait until socket is writable (i.e. connect finished) or times out
    _, writable, _ = select.select([], [sock], [], connect_timeout)
    if sock not in writable:
        messagebox.showerror("Connection Error", "Could not connect to server.")
        sock.close()
        show_frame(login_page)
        return False

    # Send the verify command
    cmd = f"v {username} {password}\n".encode()
    sock.sendall(cmd)

    # Wait for response_timeout seconds, loop until we get m 0 or m 1
    buffer = b""
    resp = None
    while True:
        readable, _, _ = select.select([sock], [], [], response_timeout)
        if not readable:
            messagebox.showerror("Connection Error", "No response from server.")
            break

        chunk = sock.recv(5454)
        if not chunk:
            break

        buffer += chunk
        if b'\n' in buffer:
            line, _ = buffer.split(b'\n', 1)
            resp = line.decode().strip()
            if resp in ("m 0", "m 1"):
                break

    sock.close()

    # Act on the response
    if resp == "m 1":
        clear_all_entries(login_page)
        show_frame(select_chat_page, username=username)
        global current_user
        current_user = username
        return 
    else:
        messagebox.showerror("Alert", "Invalid username or password.")
        show_frame(login_page)
        return 

# function to select who to chat with
def select_chat(partner_name):
    global chat_proc, current_user

    # if partner is not a user
    if partner_name not in pd.read_csv("client_side/localcache.csv")["username"].values:
        try:
            messagebox.showerror("Chat Error", "Invalid username.")
        except TclError:
            pass
        return

    # Reap a finished chat.py process
    if chat_proc is not None and chat_proc.poll() is not None:
        chat_proc = None

    # If still running, do nothing
    if chat_proc and chat_proc.poll() is None:
        return

    # Launch new chat window
    chat_proc = subprocess.Popen(
        ["python3", "chat.py", current_user, partner_name],
        start_new_session=True
    )

# funtion to get input
def get_input(entry):
    user_input = entry.get()
    print("You entered:", user_input)

# function to go back to home page after reseting everything
def go_back(page):
    clear_all_entries(page)
    show_frame(start_page)
    return

# Build the Start Page
def build_start_page():
    tk.Label(
        start_page,
        text="ChitChat 2.0",
        font=("Helvetica", 24, "bold"),
        bg="#0d1b2a",
        fg="#e0e1dd"
    ). pack(pady=50)

    # create account button
    tk.Button(
        start_page,
        text="Create Account",
        command=lambda: show_frame(create_account_page),
        **button_style
    ).pack(pady=20)

    # login to account button
    tk.Button(
        start_page,
        text="Login to Account",
        command=lambda: show_frame(login_page),
        **button_style
    ).pack(pady=20)

# Build the Create Account Page
def build_create_account_page():
    tk.Label(
        create_account_page,
        text="Create Account:",
        font=("Helvetica", 18),
        bg="#0d1b2a",
        fg="#e0e1dd"
    ).pack(pady=50)

    # getting the username
    tk.Label(
        create_account_page,
        text="Enter your username:", 
        font=("Helvetica", 12), 
        bg="#0d1b2a", fg="#e0e1dd").pack(pady=(20, 5)
    )

    username = tk.Entry(
        create_account_page,
        font=("Helvetica", 12),
        bg="#1b263b",
        fg="#e0e1dd",
        bd=0,
        insertbackground="#e0e1dd",
        width=30
    )

    username.pack(pady=(0, 20))

    # getting the password
    tk.Label(
        create_account_page,
        text="Enter a strong password:", 
        font=("Helvetica", 12), 
        bg="#0d1b2a", fg="#e0e1dd").pack(pady=(20, 5)
    )

    password =tk.Entry(
        create_account_page,
        show="*",
        font=("Helvetica", 12),
        bg="#1b263b",
        fg="#e0e1dd",
        bd=0,
        insertbackground="#e0e1dd",
        width=30
    )

    password.pack(pady=(0, 20))

    # create account button
    tk.Button(
        create_account_page,
        text="Create Account",
        command=lambda: add_account(username.get(), password.get()),
        **button_style
    ).pack(pady=20)

    # back button
    tk.Button(
        create_account_page,
        text="Back",
        command=lambda: go_back(create_account_page),
        **button_style
    ).pack(pady=20)

# Build the Login Page
def build_login_page():
    tk.Label(
        login_page,
        text="Login Page",
        font=("Helvetica", 18),
        bg="#0d1b2a",
        fg="#e0e1dd"
    ).pack(pady=50)

    # getting the username
    tk.Label(
        login_page,
        text="Enter your username:", 
        font=("Helvetica", 12), 
        bg="#0d1b2a", fg="#e0e1dd").pack(pady=(20, 5)
    )

    username = tk.Entry(
        login_page,
        font=("Helvetica", 12),
        bg="#1b263b",
        fg="#e0e1dd",
        bd=0,
        insertbackground="#e0e1dd",
        width=30
    )
    username.pack(pady=(0, 20))

    # getting the password
    tk.Label(
        login_page,
        text="Enter your password:", 
        font=("Helvetica", 12), 
        bg="#0d1b2a", fg="#e0e1dd").pack(pady=(20, 5)
    )

    password = tk.Entry(
        login_page,
        show="*",
        font=("Helvetica", 12),
        bg="#1b263b",
        fg="#e0e1dd",
        bd=0,
        insertbackground="#e0e1dd",
        width=30
    )
    password.pack(pady=(0, 20))

    # login button
    tk.Button(
        login_page,
        text="Login",
        command=lambda: login_account(username.get(), password.get()),
        **button_style
    ).pack(pady=20)

    # back button
    tk.Button(
        login_page,
        text="Back",
        command=lambda: go_back(login_page),
        **button_style
    ).pack(pady=20)

# build the select chat page
def build_select_chat_page():

    global username_label 

    username_label = tk.Label(
        select_chat_page,
        anchor="w",
        text="Logged in as:",
        font=("Helvetica", 10, "italic"),
        bg="#0d1b2a",
        fg="#808080"
    )
    username_label.pack(fill='x', padx=20, pady=(20, 5))

    # getting name of partner
    tk.Label(
        select_chat_page,
        text="Select Chat",
        font=("Helvetica", 18),
        bg="#0d1b2a",
        fg="#e0e1dd"
    ).pack(pady=50)

    partner = tk.Entry(
        select_chat_page,
        font=("Helvetica", 12),
        bg="#1b263b",
        fg="#e0e1dd",
        bd=0,
        insertbackground="#e0e1dd",
        width=30
    )
    partner.pack(pady=(0, 20))

    # start chat button
    tk.Button(
        select_chat_page,
        text="start chat",
        command=lambda: select_chat(partner.get()),
        **button_style
    ).pack(pady=20)

    # back button
    tk.Button(
        select_chat_page,
        text="back",
        command=lambda: go_back(select_chat_page),
        **button_style
    ).pack(pady=20)

# Main window
root = tk.Tk()
root.title("ChitChat 2.0")
root.geometry("500x500")
root.configure(bg="#0d1b2a")

# Common button styling
button_style = {
    "bg": "#1b263b",
    "fg": "#e0e1dd",
    "activebackground": "#415a77",
    "activeforeground": "#ffffff",
    "bd": 0,
    "font": ("Helvetica", 12),
    "width": 20,
    "height": 2,
    "cursor": "hand2"
}

# Define frames
start_page = tk.Frame(root, bg="#0d1b2a")
create_account_page = tk.Frame(root, bg="#0d1b2a")
login_page = tk.Frame(root, bg="#0d1b2a")
select_chat_page = tk.Frame(root, bg="#0d1b2a")

# Place frames in the window
for frame in (start_page, create_account_page, login_page, select_chat_page):
    frame.place(relwidth=1, relheight=1)

# Build UI for each frame
build_start_page()
build_create_account_page()
build_login_page()
build_select_chat_page()

# Start with start page
show_frame(start_page)

# Run the app
root.mainloop()
