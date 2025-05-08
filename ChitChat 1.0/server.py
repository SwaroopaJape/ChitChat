import socket
import threading
import select
import pandas as pd
import csv
import time
import os
import json

# variable declaration
HOST = '127.0.0.1'
PORT = 5454
CSV_FILE = 'server_side/users.csv'
BUFFER_DIR = 'server_side/server_chat_buffer'

COLUMNS = [
    "username", "password",
    "n1", "e1", "n2", "e2", "n3", "e3", "n4", "e4", "n5", "e5", "used"
]

file_lock    = threading.Lock()
online_pairs = set()           
user_conns   = {}

# Create the CSV file if it doesn't exist
os.makedirs(BUFFER_DIR, exist_ok=True)

# function to add user
def append_user(json_text, addr):
    try:
        data = json.loads(json_text)
        row = {
            "username": data["username"][0],
            "password": data["password"][0],
            "n1": data["n1"][0], "e1": data["e1"][0],
            "n2": data["n2"][0], "e2": data["e2"][0],
            "n3": data["n3"][0], "e3": data["e3"][0],
            "n4": data["n4"][0], "e4": data["e4"][0],
            "n5": data["n5"][0], "e5": data["e5"][0],
            "used": 0
        }
        with file_lock:
            df = pd.DataFrame([row], columns=COLUMNS)
            df.to_csv(
                CSV_FILE,
                mode='a',
                header=not pd.io.common.file_exists(CSV_FILE),
                index=False,
                quoting=csv.QUOTE_MINIMAL
            )
        print(f"[{time.time()}] [{addr}] Appended user: {row}")
    except Exception as e:
        print(f"[{time.time()}] [{addr}] append_user error: {e}")

# function to verify user
def verify_user(text, addr, conn):
    try:
        username, password = text.strip().split(" ", 1)
        with file_lock:
            df = pd.read_csv(CSV_FILE, dtype=str)
        df.columns = df.columns.str.strip().str.replace('"','').str.replace("'","")
        match = df[(df.username==username)&(df.password==password)]
        if not match.empty:
            conn.sendall(b"m 1\n")
        else:
            conn.sendall(b"m 0\n")
    except:
        try: conn.sendall(b"m 0\n")
        except: pass

# function to allocate keys
def allocate_key(username):
    with file_lock:
        df = pd.read_csv(CSV_FILE, dtype=str, skipinitialspace=True)
    df.columns = df.columns.str.strip().str.replace('"','').str.replace("'","")
    df['used'] = df.get('used', 0).astype(int)
    row = df[df.username==username]
    if row.empty:
        return None, None
    used = int(row.iloc[0].used)
    idx = (used % 5) + 1
    n = row.iloc[0][f'n{idx}']
    e = row.iloc[0][f'e{idx}']
    df.loc[df.username==username, 'used'] = used + 1
    with file_lock:
        df.to_csv(CSV_FILE, index=False)
    return n, e

# function to send buffered messages
def send_buffered_messages(user, partner, conn):
    path = f"{BUFFER_DIR}/{partner}_{user}.txt"
    if os.path.exists(path):
        with open(path, 'r') as f:
            for line in f:
                try:
                    conn.sendall(line.encode())
                except:
                    break
        os.remove(path)

# function to handle login
def handle_login(cmd, conn):
    _, user, partner = cmd.split()
    online_pairs.add((user, partner))
    user_conns[user] = conn
    send_buffered_messages(user, partner, conn)

# function to handle logout
def handle_logout(cmd):
    _, user, partner = cmd.split()
    online_pairs.discard((user, partner))
    user_conns.pop(user, None)

# function to handle message sending
def handle_send(cmd, conn):
    parts = cmd.split(" ", 4)
    if len(parts) < 5:
        return
    _, sender, recipient, ts, msg = parts
    reply = f"msg {sender} {recipient} {ts} {msg}\n"

    # live-forward if online
    other = user_conns.get(recipient)
    if other:
        try:
            other.sendall(reply.encode())
        except:
            pass
    else:
        # only buffer if recipient is offline
        buf = f"{BUFFER_DIR}/{sender}_{recipient}.txt"
        with open(buf, 'a') as f:
            f.write(reply)

# function to handle new chat
def handle_newchat(cmd, conn):
    _, user, partner = cmd.split()
    buf_path = f"{BUFFER_DIR}/{partner}_{user}.txt"
    if os.path.exists(buf_path):
        with open(buf_path, 'r') as f:
            for line in f:
                try: conn.sendall(line.encode())
                except: break
        os.remove(buf_path)
        return

    n1, e1 = allocate_key(user)
    n2, e2 = allocate_key(partner)
    if None in (n1, e1, n2, e2):
        return

    # send EK to initiator
    conn.sendall(f"ek {user} {n1} {e1} {n2} {e2}\n".encode())
    # buffer swapped EK for partner
    ekp = f"ek {partner} {n2} {e2} {n1} {e1}\n"
    with open(f"{BUFFER_DIR}/{user}_{partner}.txt", 'w') as f:
        f.write(ekp)

# function to handle client connections
def handle_client(conn, addr):
    conn.setblocking(False)
    buf = b''
    while True:
        try:
            ready, _, _ = select.select([conn], [], [], 0.5)
            if not ready:
                continue
            data = conn.recv(4096)
            if not data:
                break
            buf += data
            while b'\n' in buf:
                line, buf = buf.split(b'\n', 1)
                text = line.decode().strip()
                if text.startswith("a "):
                    append_user(text[2:], addr)
                elif text.startswith("v "):
                    verify_user(text[2:], addr, conn)
                elif text.startswith("l "):
                    handle_login(text, conn)
                elif text.startswith("nl "):
                    handle_logout(text)
                elif text.startswith("msg "):
                    handle_send(text, conn)
                elif text.startswith("nc "):
                    handle_newchat(text, conn)
        except:
            break
    conn.close()

# function to start the server
def start_server():
    with socket.socket() as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Server listening on {HOST}:{PORT}")
        while True:
            conn, addr = s.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr))
            t.daemon = True
            t.start()


if __name__ == "__main__":
    start_server()
