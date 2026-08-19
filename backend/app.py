"""
FLEXIFIT backend
=================
Serves the static multipage frontend and exposes a small JSON API that
stores contact inquiries and membership applications in a SQLite database.

Every new submission also triggers a "notification":
  - it is always printed to the server console and logged to notifications.log
  - if SMTP environment variables are configured, an email is also sent
    to the gym's staff inbox

An in-app dashboard at /admin (protected by a real login page, not the
browser's Basic Auth popup) lists every inquiry and membership application,
and updates itself automatically every few seconds.

Run with:
    pip install -r requirements.txt
    python app.py
Then open http://localhost:5000
"""

import os
import re
import sqlite3
import smtplib
import logging
from email.message import EmailMessage
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, request, jsonify, g, send_from_directory,
    render_template_string, session, redirect
)
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend")
DB_PATH = os.path.join(BASE_DIR, "flexifit.db")
LOG_PATH = os.path.join(BASE_DIR, "notifications.log")

GYM_NAME = "FLEXIFIT"
STAFF_NOTIFY_EMAIL = os.environ.get("FLEXIFIT_NOTIFY_EMAIL", "frontdesk@flexifitgym.in")

SMTP_HOST = os.environ.get("FLEXIFIT_SMTP_HOST")
SMTP_PORT = int(os.environ.get("FLEXIFIT_SMTP_PORT", "587"))
SMTP_USER = os.environ.get("FLEXIFIT_SMTP_USER")
SMTP_PASS = os.environ.get("FLEXIFIT_SMTP_PASS")
SMTP_FROM = os.environ.get("FLEXIFIT_SMTP_FROM", SMTP_USER)

ADMIN_PASSWORD = os.environ.get("FLEXIFIT_ADMIN_PASSWORD", "flexifit-admin")

logging.basicConfig(filename=LOG_PATH, level=logging.INFO, format="%(asctime)s | %(message)s")

app = Flask(__name__, static_folder=None)
CORS(app)
app.secret_key = os.environ.get("FLEXIFIT_SECRET_KEY", "flexifit-dev-secret-change-me")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS contact_inquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            subject TEXT,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'new'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS membership_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            plan TEXT NOT NULL,
            goal TEXT,
            start_date TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'new'
        )
    """)
    conn.commit()
    conn.close()


init_db()


def notify(kind, record):
    summary = f"NEW {kind.upper()} — {record.get('name')} ({record.get('email')})"
    print(f"[FLEXIFIT NOTIFY] {summary}")
    logging.info(summary + " | " + str(record))
    if SMTP_HOST and SMTP_USER and SMTP_PASS:
        try:
            send_email_notification(kind, record)
        except Exception as exc:
            print(f"[FLEXIFIT NOTIFY] email failed: {exc}")
            logging.info(f"email notification failed: {exc}")


def send_email_notification(kind, record):
    msg = EmailMessage()
    msg["Subject"] = f"[{GYM_NAME}] New {kind} — {record.get('name')}"
    msg["From"] = SMTP_FROM
    msg["To"] = STAFF_NOTIFY_EMAIL
    lines = [f"{k}: {v}" for k, v in record.items() if k != "id"]
    msg.set_content("A new submission was received on the website:\n\n" + "\n".join(lines))
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)


@app.route("/")
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:filename>")
def frontend_files(filename):
    if os.path.isfile(os.path.join(FRONTEND_DIR, filename)):
        return send_from_directory(FRONTEND_DIR, filename)
    return jsonify({"error": "Not found"}), 404


@app.route("/api/contact", methods=["POST"])
def api_contact():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip()
    subject = (data.get("subject") or "General inquiry").strip()
    message = (data.get("message") or "").strip()

    if not name or not email or not message:
        return jsonify({"error": "Name, email and message are required."}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"error": "Please enter a valid email address."}), 400

    created_at = datetime.utcnow().isoformat()
    db = get_db()
    cur = db.execute(
        "INSERT INTO contact_inquiries (name, email, phone, subject, message, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (name, email, phone, subject, message, created_at),
    )
    db.commit()

    record = {"id": cur.lastrowid, "name": name, "email": email, "phone": phone,
              "subject": subject, "message": message, "created_at": created_at}
    notify("contact inquiry", record)
    return jsonify({"success": True, "id": cur.lastrowid}), 201


@app.route("/api/membership", methods=["POST"])
def api_membership():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip()
    plan = (data.get("plan") or "").strip()
    goal = (data.get("goal") or "").strip()
    start_date = (data.get("start_date") or "").strip()
    notes = (data.get("notes") or "").strip()

    if not name or not email or not phone or not plan:
        return jsonify({"error": "Name, email, phone and plan are required."}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"error": "Please enter a valid email address."}), 400

    created_at = datetime.utcnow().isoformat()
    db = get_db()
    cur = db.execute(
        "INSERT INTO membership_applications "
        "(name, email, phone, plan, goal, start_date, notes, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (name, email, phone, plan, goal, start_date, notes, created_at),
    )
    db.commit()

    record = {"id": cur.lastrowid, "name": name, "email": email, "phone": phone,
              "plan": plan, "goal": goal, "start_date": start_date,
              "notes": notes, "created_at": created_at}
    notify("membership application", record)
    return jsonify({"success": True, "id": cur.lastrowid}), 201


def require_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect("/admin/login")
        return fn(*args, **kwargs)
    return wrapper


def format_ist(iso_str):
    try:
        dt_ist = datetime.fromisoformat(iso_str) + timedelta(hours=5, minutes=30)
    except (TypeError, ValueError):
        return "-", "-"
    return dt_ist.strftime("%d %b %Y"), dt_ist.strftime("%I:%M %p")


def membership_to_dict(m):
    date, time = format_ist(m["created_at"])
    return {"date": date, "time": time, "name": m["name"], "phone": m["phone"],
            "email": m["email"], "plan": m["plan"], "goal": m["goal"],
            "start_date": m["start_date"], "notes": m["notes"]}


def inquiry_to_dict(c):
    date, time = format_ist(c["created_at"])
    return {"date": date, "time": time, "name": c["name"], "phone": c["phone"],
            "email": c["email"], "subject": c["subject"], "message": c["message"]}


LOGIN_TEMPLATE = """
<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>Admin Login — FLEXIFIT</title>
<style>
  body{ font-family:'JetBrains Mono', monospace; background:#0B0B0C; color:#F3F0E7;
        display:flex; align-items:center; justify-content:center; height:100vh; margin:0; }
  form{ background:#19191B; border:1px solid #333; padding:36px 34px; width:280px; }
  h1{ color:#F5C400; font-size:16px; margin:0 0 22px; text-transform:uppercase; letter-spacing:1px; }
  label{ display:block; font-size:11px; color:#999; text-transform:uppercase; letter-spacing:1px; margin-bottom:6px; }
  input{ width:100%; background:#0B0B0C; border:1px solid #333; color:#F3F0E7; padding:10px 12px;
         font-family:inherit; font-size:14px; box-sizing:border-box; margin-bottom:18px; }
  input:focus{ outline:none; border-color:#F5C400; }
  button{ width:100%; background:#F5C400; color:#000; border:0; padding:12px; font-weight:bold;
          text-transform:uppercase; letter-spacing:1px; font-size:12px; cursor:pointer; }
  .err{ color:#E1442C; font-size:12px; margin-bottom:16px; }
</style></head><body>
<form method="POST">
  <h1>FLEXIFIT Admin</h1>
  {% if error %}<p class="err">{{ error }}</p>{% endif %}
  <label for="password">Password</label>
  <input type="password" id="password" name="password" autofocus required>
  <button type="submit">Sign In</button>
</form>
</body></html>
"""


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["is_admin"] = True
            return redirect("/admin")
        error = "Incorrect password."
    return render_template_string(LOGIN_TEMPLATE, error=error)


@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    return redirect("/admin/login")


ADMIN_TEMPLATE = """
<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>FLEXIFIT — Admin Dashboard</title>
<style>
  body{ font-family:'JetBrains Mono', monospace; background:#0B0B0C; color:#F3F0E7; margin:0; padding:40px; }
  h1{ color:#F5C400; font-size:22px; display:inline-block; }
  .topbar{ display:flex; justify-content:space-between; align-items:baseline; flex-wrap:wrap; gap:12px; }
  .logout{ color:#F5C400; font-size:12px; text-decoration:underline; text-transform:uppercase; letter-spacing:1px; }
  h2{ color:#F5C400; font-size:16px; margin-top:40px; border-bottom:1px solid #333; padding-bottom:10px; display:flex; justify-content:space-between; align-items:baseline;}
  table{ width:100%; border-collapse:collapse; margin-top:16px; font-size:13px; }
  th,td{ border:1px solid #333; padding:10px; text-align:left; vertical-align:top; white-space:nowrap; }
  td.wrap{ white-space:normal; }
  th{ background:#19191B; color:#F5C400; text-transform:uppercase; letter-spacing:1px; font-size:11px;}
  tr:hover{ background:#19191B; }
  .empty{ color:#888; padding:20px 0; }
  .live{ font-size:11px; color:#888; display:flex; align-items:center; gap:6px; }
  .dot{ width:7px; height:7px; border-radius:50%; background:#F5C400; animation:pulse 1.5s ease-in-out infinite; }
  @keyframes pulse{ 0%,100%{opacity:1;} 50%{opacity:.25;} }
</style></head><body>

<div class="topbar">
  <h1>FLEXIFIT — Admin Dashboard</h1>
  <a class="logout" href="/admin/logout">Log out</a>
</div>
<p class="live"><span class="dot"></span><span id="live-status">Live — updated just now</span></p>

<h2><span>Membership Applications (<span id="m-count">{{ memberships|length }}</span>)</span></h2>
<table id="m-table" style="display:{{ 'table' if memberships else 'none' }};">
<tr><th>Date</th><th>Time</th><th>Name</th><th>Phone</th><th>Email</th><th>Plan</th><th>Goal</th><th>Start</th><th>Notes</th></tr>
<tbody id="m-body">
{% for m in memberships %}
<tr>
  <td>{{ m['date'] }}</td><td>{{ m['time'] }}</td><td>{{ m['name'] }}</td><td>{{ m['phone'] }}</td>
  <td>{{ m['email'] }}</td><td>{{ m['plan'] }}</td><td>{{ m['goal'] }}</td>
  <td>{{ m['start_date'] }}</td><td class="wrap">{{ m['notes'] }}</td>
</tr>
{% endfor %}
</tbody>
</table>
<p class="empty" id="m-empty" style="display:{{ 'none' if memberships else 'block' }};">No membership applications yet.</p>

<h2><span>Contact Inquiries (<span id="c-count">{{ inquiries|length }}</span>)</span></h2>
<table id="c-table" style="display:{{ 'table' if inquiries else 'none' }};">
<tr><th>Date</th><th>Time</th><th>Name</th><th>Phone</th><th>Email</th><th>Subject</th><th>Message</th></tr>
<tbody id="c-body">
{% for c in inquiries %}
<tr>
  <td>{{ c['date'] }}</td><td>{{ c['time'] }}</td><td>{{ c['name'] }}</td><td>{{ c['phone'] }}</td>
  <td>{{ c['email'] }}</td><td>{{ c['subject'] }}</td><td class="wrap">{{ c['message'] }}</td>
</tr>
{% endfor %}
</tbody>
</table>
<p class="empty" id="c-empty" style="display:{{ 'none' if inquiries else 'block' }};">No contact inquiries yet.</p>

<script>
function cell(text) {
  var td = document.createElement('td');
  td.textContent = text || '';
  return td;
}
function renderTable(tbodyId, tableId, emptyId, rows, columns) {
  var tbody = document.getElementById(tbodyId);
  tbody.innerHTML = '';
  rows.forEach(function (row) {
    var tr = document.createElement('tr');
    columns.forEach(function (key) { tr.appendChild(cell(row[key])); });
    tbody.appendChild(tr);
  });
  document.getElementById(tableId).style.display = rows.length ? 'table' : 'none';
  document.getElementById(emptyId).style.display = rows.length ? 'none' : 'block';
}
function refreshDashboard() {
  fetch('/api/admin/data')
    .then(function (res) {
      if (res.status === 401 || res.redirected) { window.location.href = '/admin/login'; return null; }
      return res.json();
    })
    .then(function (data) {
      if (!data) return;
      renderTable('m-body', 'm-table', 'm-empty', data.memberships,
        ['date','time','name','phone','email','plan','goal','start_date','notes']);
      renderTable('c-body', 'c-table', 'c-empty', data.inquiries,
        ['date','time','name','phone','email','subject','message']);
      document.getElementById('m-count').textContent = data.memberships.length;
      document.getElementById('c-count').textContent = data.inquiries.length;
      document.getElementById('live-status').textContent =
        'Live — updated ' + new Date().toLocaleTimeString();
    })
    .catch(function () {
      document.getElementById('live-status').textContent = 'Live — connection lost, retrying...';
    });
}
setInterval(refreshDashboard, 8000);
</script>

</body></html>
"""


@app.route("/admin")
@require_admin
def admin_dashboard():
    db = get_db()
    memberships = [membership_to_dict(m) for m in db.execute(
        "SELECT * FROM membership_applications ORDER BY id DESC").fetchall()]
    inquiries = [inquiry_to_dict(c) for c in db.execute(
        "SELECT * FROM contact_inquiries ORDER BY id DESC").fetchall()]
    return render_template_string(ADMIN_TEMPLATE, memberships=memberships, inquiries=inquiries)


@app.route("/api/admin/data")
@require_admin
def api_admin_data():
    db = get_db()
    memberships = [membership_to_dict(m) for m in db.execute(
        "SELECT * FROM membership_applications ORDER BY id DESC").fetchall()]
    inquiries = [inquiry_to_dict(c) for c in db.execute(
        "SELECT * FROM contact_inquiries ORDER BY id DESC").fetchall()]
    return jsonify({"memberships": memberships, "inquiries": inquiries})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"FLEXIFIT server running — open http://localhost:{port}")
    print(f"Admin dashboard: http://localhost:{port}/admin  (password: {ADMIN_PASSWORD})")
    app.run(host="0.0.0.0", port=port, debug=True)
