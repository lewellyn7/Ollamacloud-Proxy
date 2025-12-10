import sqlite3
import hashlib
import uuid
import time
from typing import List, Optional

DB_FILE = "data/proxy.db"

def get_connection():
    return sqlite3.connect(DB_FILE, timeout=10)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS api_keys (key TEXT PRIMARY KEY, name TEXT, user_id TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password_hash TEXT,
        email TEXT UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        reg_ip TEXT,
        failed_attempts INTEGER DEFAULT 0,
        locked_until REAL DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, username TEXT, expires_at REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS blocked_ips (ip TEXT PRIMARY KEY, blocked_until REAL, reason TEXT)''')
    c.execute("INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)", ("ollama_host", "https://ollama.com/api/chat"))
    c.execute("SELECT count(*) FROM users")
    if c.fetchone()[0] == 0:
        default_pass = hash_password("admin")
        c.execute("INSERT INTO users (username, password_hash, email, reg_ip) VALUES (?, ?, ?, ?)",
                  ("admin", default_pass, "admin@local", "127.0.0.1"))
    conn.commit()
    conn.close()

def get_config(key: str) -> Optional[str]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM config WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def set_config(key: str, value: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def is_ip_blocked(ip: str) -> bool:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT blocked_until FROM blocked_ips WHERE ip=?", (ip,))
    row = c.fetchone()
    conn.close()
    if row:
        if time.time() < row[0]: return True
        else: unblock_ip(ip)
    return False

def block_ip(ip: str, duration: int = 1800, reason: str = "Login Failed"):
    conn = get_connection()
    c = conn.cursor()
    blocked_until = time.time() + duration
    c.execute("INSERT OR REPLACE INTO blocked_ips (ip, blocked_until, reason) VALUES (?, ?, ?)", (ip, blocked_until, reason))
    conn.commit()
    conn.close()

def unblock_ip(ip: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM blocked_ips WHERE ip=?", (ip,))
    conn.commit()
    conn.close()

def check_registration_limit(ip: str) -> bool:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT count(*) FROM users WHERE reg_ip=?", (ip,))
    count = c.fetchone()[0]
    conn.close()
    return count < 5

def create_user(username, password, email, ip):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_hash, email, reg_ip) VALUES (?, ?, ?, ?)",
                  (username, hash_password(password), email, ip))
        conn.commit()
        return True, "注册成功"
    except sqlite3.IntegrityError as e:
        if "email" in str(e): return False, "该邮箱已被注册"
        return False, "用户名已存在"
    finally: conn.close()

def verify_login_security(username, password, ip):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT password_hash, failed_attempts, locked_until FROM users WHERE username=?", (username,))
    row = c.fetchone()
    if not row:
        conn.close()
        return False, "用户名或密码错误"
    real_hash, failed_attempts, locked_until = row

    if time.time() < locked_until:
        conn.close()
        return False, f"账号锁定中，请等待 {int(locked_until - time.time())} 秒"

    if real_hash == hash_password(password):
        c.execute("UPDATE users SET failed_attempts=0, locked_until=0 WHERE username=?", (username,))
        conn.commit()
        conn.close()
        return True, "success"
    else:
        new_attempts = failed_attempts + 1
        if new_attempts >= 5:
            lock_time = time.time() + 1800
            c.execute("UPDATE users SET failed_attempts=?, locked_until=? WHERE username=?", (new_attempts, lock_time, username))
            conn.commit()
            conn.close()
            block_ip(ip, duration=1800, reason="Too many login failures")
            return False, "错误次数过多，账号及IP已被封锁 30 分钟"
        else:
            c.execute("UPDATE users SET failed_attempts=? WHERE username=?", (new_attempts, username))
            conn.commit()
            conn.close()
            return False, f"密码错误 (剩余次数: {5 - new_attempts})"

# --- 新增：修改密码函数 ---
def change_user_password(username, old_password, new_password):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE username=?", (username,))
    row = c.fetchone()
    if not row:
        conn.close()
        return False, "用户不存在"

    current_hash = row[0]
    if current_hash != hash_password(old_password):
        conn.close()
        return False, "旧密码错误"

    c.execute("UPDATE users SET password_hash=? WHERE username=?", (hash_password(new_password), username))
    conn.commit()
    conn.close()
    return True, "密码修改成功"

def create_session(username):
    token = str(uuid.uuid4())
    expires = time.time() + (2592000)
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO sessions (token, username, expires_at) VALUES (?, ?, ?)", (token, username, expires))
    conn.commit()
    conn.close()
    return token

def get_session_user(token):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT username FROM sessions WHERE token=? AND expires_at > ?", (token, time.time()))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def delete_session(token):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM sessions WHERE token=?", (token,))
    conn.commit()
    conn.close()

def create_api_key(key, name, user_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO api_keys (key, name, user_id) VALUES (?, ?, ?)", (key, name, user_id))
        conn.commit()
        return True
    except: return False
    finally: conn.close()

def list_api_keys(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT key, name, created_at FROM api_keys WHERE user_id=? ORDER BY created_at DESC", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [{"key": r[0], "name": r[1], "created_at": r[2]} for r in rows]

def verify_api_key(key):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT 1 FROM api_keys WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row is not None

def delete_api_key(key, user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM api_keys WHERE key=? AND user_id=?", (key, user_id))
    conn.commit()
    conn.close()
