import socket
import threading
import select
import pandas as pd
import csv
import time
import os
import json
import random
import rsamodule as rsa

# variable declaration
HOST = '127.0.0.1'
PORT = 5454
CSV_FILE = 'server_side/users.csv'
BUFFER_DIR = 'server_side/server_chat_buffer'
ENCRYPTION_DIR = 'chat_encryption.csv'

COLUMNS = ["username", "password", "n", "e"]

file_lock    = threading.Lock()
online_pairs = set()           
user_conns   = {}

# Create the CSV file if it doesn't exist
os.makedirs(BUFFER_DIR, exist_ok=True)

# function to add user
def append_user(json_text, addr):
    try:
        data = json.loads(json_text)
        username = data.get("username")
        password = data.get("password")
        n = data.get("n")
        e = data.get("e")
        if None in (username, password, n, e):
            raise ValueError("registration JSON missing one of username/password/n/e")

        # append to users.csv under the file lock
        with file_lock, open(CSV_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([username, password, n, e])

    except Exception as exc:
        print(f"[{time.time()}] [{addr}] append_user error: {exc}")


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
def allocate_key(user, partner):
    filepath = 'server_side/chat_encryption.csv'
    if not os.path.exists(filepath):
        pd.DataFrame(columns=["pair","key"]).to_csv(filepath, index=False)
    df = pd.read_csv(filepath, dtype=str)

    pair1, pair2 = f"{user}_{partner}", f"{partner}_{user}"
    # if existing
    if pair1 in df['pair'].values:
        return int(df.loc[df['pair']==pair1, 'key'].iloc[0])
    if pair2 in df['pair'].values:
        return int(df.loc[df['pair']==pair2, 'key'].iloc[0])

    # otherwise generate, append, return
    key = random.randint(0, 1023)
    new = pd.DataFrame([{"pair":pair1,"key":key},{"pair":pair2,"key":key}])
    pd.concat([df,new], ignore_index=True).to_csv(filepath, index=False)
    return key


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
    _, user, partner = cmd.strip().split()

    # generate (or fetch) the raw SDES key
    raw_key = allocate_key(user, partner)

    # look up this user's RSA pubkey
    df = pd.read_csv(CSV_FILE, dtype=str)
    row = df[df['username']==user].iloc[0]
    n, e = int(row['n']), int(row['e'])

    # encrypt it
    cipher = rsa.encrypt(raw_key, n, e)
    ek_line = f"ek {user} {cipher}\n"
    conn.sendall(ek_line.encode())

    # also buffer it for the partner exactly the same way
    partner_buf = f"{BUFFER_DIR}/{user}_{partner}.txt"
    with open(partner_buf, 'a') as f:
        f.write(ek_line)

## function to handle client connections
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
