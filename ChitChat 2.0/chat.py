import sys
import os
import csv
import socket
import threading
import time
import pandas as pd
import sdesmodule as sdes
import rsamodule as rsa

from tkinter import Tk, Entry, Button, Frame, END, BOTH, LEFT, RIGHT, X
from tkinter.scrolledtext import ScrolledText

# if proper arguments not available
if len(sys.argv) < 3:
    print("Usage: python chat.py <user> <partner>")
    sys.exit(1)

# global variables
global partner, user
partner = sys.argv[2]
user = sys.argv[1]

# funtion to display messages in gui
def display_message(sender, ts, msg):
    
    ts_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(ts)))
    colour_tag = 'user' if sender == user else 'partner'
    text_area.configure(state='normal')

    text_area.insert(END, sender, 'meta')
    text_area.insert(END, f"[{ts_str}]: ", 'meta')
    
    text_area.insert(END, msg + "\n\n", colour_tag)

    text_area.see(END)
    text_area.configure(state='disabled')

# funtion to send msgs for chat to server
def on_send(event=None):
    global running

    # load partner’s public key
    df = pd.read_csv(partners_csv, dtype=str, skipinitialspace=True)
    row = df[df["Partner"] == partner].iloc[0]
    key = int(row["key"])

    # grab your plaintext
    msg = entry.get().strip()
    if not msg or not running:
        return
    entry.delete(0, END)

    # encrypt for the server
    ts = time.time()
    ciphertext = sdes.encryptmsg(key, msg)
    out = f"msg {user} {partner} {ts} {ciphertext}\n"

    try:
        sock.sendall(out.encode())
    except:
        running = False

    # store your plaintext
    with open(chat_file, 'a') as f:
        f.write(f"msg {user} {partner} {ts} {msg}\n")

    # display your plaintext immediately
    display_message(user, ts, msg)

# while closing the chat
def on_close():
    global running
    running = False
    try:
        sock.sendall(f"nl {user} {partner}\n".encode())
    except:
        pass
    try:
        sock.close()
    except:
        pass
    root.destroy()

# to listen to incoming msgs while online
def recv_loop():
    global running

    # Load decryption params for this partner
    df = pd.read_csv(partners_csv, dtype=str, skipinitialspace=True)
    row = df[df["Partner"] == partner].iloc[0]
    key = int(row["key"])

    buf = ""
    while running:
        try:
            data = sock.recv(4096).decode()
        except:
            break
        if not data:
            time.sleep(0.1)
            continue

        buf += data
        while "\n" in buf:
            line, buf = buf.split("\n", 1)
            if not line.startswith("msg "):
                continue

            _, snd, rcv, ts, ciphertext = line.split(" ", 4)
            if rcv != user:
                continue

            # Always store the raw ciphertext line
            with open(chat_file, 'a') as f:
                f.write(line + "\n")

            # Decrypt only partner’s messages for display
            if snd == partner:
                to_show = sdes.decryptmsg(key, ciphertext)
            else:
                # if somehow echoing your own, just show plaintext
                to_show = ciphertext

            # Display (plaintext for partner, ciphertext for self)
            text_area.after(0, display_message, snd, ts, to_show)

# function to load all the older msgs
def load_history():
    # read your private key once
    df = pd.read_csv(partners_csv, dtype=str, skipinitialspace=True)
    row = df[df["Partner"] == partner].iloc[0]
    key = int(row["key"])

    # iterate stored messages
    with open(chat_file, 'r') as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            parts = raw.split(" ", 4)
            if len(parts) < 5:
                continue
            _, snd, rcv, ts, ciphertext = parts

            if snd == partner:
                try:
                    # finding encrypted msgs
                    test_val = ciphertext.strip().split()
                    _ = [int(x) for x in test_val]
                    text = sdes.decryptmsg(key, ciphertext)
                except ValueError:
                    # already plaintext i.e. user sent msg
                    text = ciphertext  
            else:
                text = ciphertext  

            display_message(snd, ts, text)

# declaring variables
user, partner = sys.argv[1], sys.argv[2]
SERVER_IP, SERVER_PORT = "127.0.0.1", 5454

# declaring paths
partners_csv = f"client_side/chat_encryption/{user}_partners.csv"
chat_dir = f"client_side/chats/{user}"
chat_file = f"{chat_dir}/{partner}.txt"
encryption_file = "chat_encryption.csv"

# creating required directories and files
os.makedirs(os.path.dirname(partners_csv), exist_ok=True)
os.makedirs(chat_dir, exist_ok=True)

if not os.path.exists(partners_csv):
    with open(partners_csv, 'w', newline='') as f:
        csv.writer(f).writerow(["Partner","key"])

with open(partners_csv) as f:
    existing = {r[0] for r in csv.reader(f) if r and r[0]!="Partner"}

# creating socket
sock = socket.socket()
sock.connect((SERVER_IP, SERVER_PORT))

# if partner not in existing
if partner not in existing:
    # ask server to generate & send a fresh S‑DES key
    sock.sendall(f"nc {user} {partner}\n".encode())

    # receive the server‑generated key
    buf = ""
    sdes_key = None
    while sdes_key is None:
        buf += sock.recv(4096).decode()
        
        while "\n" in buf:
            line, buf = buf.split("\n", 1)
            parts = line.strip().split()
            
            if parts[0] == "ek" and parts[1].strip() == user:
                sdes_key = parts[2].strip()
                filename = f"client_side/rsakeys/{user}.txt"
                with open(filename, 'r') as f:
                    line = f.readline().strip()
                    n_str, e_str, d_str = line.split(", ") 
                n = int(n_str)
                e = int(e_str)
                d = int(d_str)
                sdes_key = rsa.decrypt(int(sdes_key), n, d)
                break

    # store the new symmetric key in partners_csv
    with open(partners_csv, 'a', newline='') as f:
        csv.writer(f).writerow([partner, sdes_key])


# if partner is in existing
sock.sendall(f"l {user} {partner}\n".encode())
open(chat_file, 'a').close()
running = True

root = Tk()
root.title(f"{user} - {partner}")
root.geometry("600x600")
root.configure(bg="#0d1b2a")   # window bg

# ScrolledText with styling
text_area = ScrolledText(
    root,
    wrap='word',
    state='disabled',
    bg="#1b263b",             
    fg="#e0e1dd",             
    insertbackground="#e0e1dd",  
    selectbackground="#415a77",
    font=("Helvetica", 10),
    bd=0,
    highlightthickness=0
)
text_area.pack(fill=BOTH, expand=True, padx=5, pady=5)

# Style the vertical scrollbar
text_area.vbar.config(
    bg="#415a77",           
    troughcolor="#0d1b2a",  
    activebackground="#778da9",
    width=12,
    bd=0,
    relief="flat",
    highlightthickness=0
)

# Text tags
text_area.tag_configure('meta',
    font=("Helvetica", 10, "bold"),
    foreground="#e0e1dd"
)
text_area.tag_configure('user',
    font=("Helvetica", 10),
    foreground="#acadad",
    justify='right',
    spacing1=5, spacing3=10
)
text_area.tag_configure('partner',
    font=("Helvetica", 10),
    foreground="#ffd60a",
    justify='left',
    spacing1=5, spacing3=10
)

# Bottom entry + send button
frm = Frame(root, bg="#0d1b2a")
frm.pack(fill=X, padx=5, pady=5)

# Entry for message input
entry = Entry(
    frm,
    bg="#1b263b",
    fg="#e0e1dd",
    insertbackground="#e0e1dd",
    relief="flat",
    font=("Helvetica", 10)
)
entry.pack(side=LEFT, fill=X, expand=True, padx=(0,5))

btn = Button(
    frm,
    text="Send",
    bg="#415a77",
    fg="#ffffff",
    relief="flat",
    activebackground="#778da9",
    cursor="hand2",
    font=("Helvetica", 10)
)
btn.pack(side=RIGHT)

# Load existing messages
load_history()

# Bind events
btn.config(command=on_send)
entry.bind('<Return>', on_send)
root.protocol("WM_DELETE_WINDOW", on_close)

# Start the recv loop in a separate thread
threading.Thread(target=recv_loop, daemon=True).start()
root.mainloop()
