"""
FLEXIFIT backend
=================
...
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
    render_template_string, Response
)
from flask_cors import CORS

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
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

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s | %(message)s"
)

app = Flask(__name__, static_folder=None)
CORS(app)  # ← only ONE app is ever created now, and it has CORS

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Notification layer — console/log always, email if SMTP is configured
# ---------------------------------------------------------------------------
def notify(kind, record):
    """Notify staff of a new inquiry/membership submission."""
    summary = f"NEW {kind.upper()} — {record.get('name')} ({record.get('email')})"
    print(f"[FLEXIFIT NOTIFY] {summary}")
    logging.info(summary + " | " + str(record))

    if SMTP_HOST and SMTP_USER and SMTP_PASS:
        try:
            send_email_notification(kind, record)
        except Exception as exc:  # noqa: BLE001 — never let email break the request
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


# ---------------------------------------------------------------------------
# Static frontend routes — each page is its own HTML file, served as-is
# ---------------------------------------------------------------------------
@app.route("/")
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:filename>")
def frontend_files(filename):
    # Serves index.html, about.html, .../css/style.css, /js/*.js, etc.
    if os.path.isfile(os.path.join(FRONTEND_DIR, filename)):
        return send_from_directory(FRONTEND_DIR, filename)
    return jsonify({"error": "Not found"}), 404


# ---------------------------------------------------------------------------
# API — contact inquiries
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# API — membership applications
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Minimal admin dashboard — password gated, shows both tables
# ---------------------------------------------------------------------------
def require_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.authorization
        if not auth or auth.password != ADMIN_PASSWORD:
            return Response(
                "Authentication required.", 401,
                {"WWW-Authenticate": 'Basic realm="FLEXIFIT Admin"'}
            )
        return fn(*args, **kwargs)
    return wrapper


ADMIN_TEMPLATE = """
<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>FLEXIFIT — Admin Dashboard</title>
<style>
  body{ font-family:'JetBrains Mono', monospace; background:#0B0B0C; color:#F3F0E7; margin:0; padding:40px; }
  h1{ color:#F5C400; font-size:22px; }
  h2{ color:#F5C400; font-size:16px; margin-top:40px; border-bottom:1px solid #333; padding-bottom:10px;}
  table{ width:100%; border-collapse:collapse; margin-top:16px; font-size:13px; }
  th,td{ border:1px solid #333; padding:10px; text-align:left; vertical-align:top; }
  th{ background:#19191B; color:#F5C400; text-transform:uppercase; letter-spacing:1px; font-size:11px;}
  tr:hover{ background:#19191B; }
  .empty{ color:#888; padding:20px 0; }
</style></head><body>
<h1>FLEXIFIT — Admin Dashboard</h1>
<p style="color:#999;">Newest submissions first. Refresh to see new leads. This page is Basic-Auth protected — do not expose it publicly without changing FLEXIFIT_ADMIN_PASSWORD.</p>

<h2>Membership Applications ({{ memberships|length }})</h2>
{% if memberships %}
<table>
<tr><th>Date</th><th>Name</th><th>Phone</th><th>Email</th><th>Plan</th><th>Goal</th><th>Start</th><th>Notes</th></tr>
{% for m in memberships %}
<tr>
  <td>{{ m['created_at'] }}</td><td>{{ m['name'] }}</td><td>{{ m['phone'] }}</td>
  <td>{{ m['email'] }}</td><td>{{ m['plan'] }}</td><td>{{ m['goal'] }}</td>
  <td>{{ m['start_date'] }}</td><td>{{ m['notes'] }}</td>
</tr>
{% endfor %}
</table>
{% else %}<p class="empty">No membership applications yet.</p>{% endif %}

<h2>Contact Inquiries ({{ inquiries|length }})</h2>
{% if inquiries %}
<table>
<tr><th>Date</th><th>Name</th><th>Phone</th><th>Email</th><th>Subject</th><th>Message</th></tr>
{% for c in inquiries %}
<tr>
  <td>{{ c['created_at'] }}</td><td>{{ c['name'] }}</td><td>{{ c['phone'] }}</td>
  <td>{{ c['email'] }}</td><td>{{ c['subject'] }}</td><td>{{ c['message'] }}</td>
</tr>
{% endfor %}
</table>
{% else %}<p class="empty">No contact inquiries yet.</p>{% endif %}

</body></html>
"""


@app.route("/admin")
@require_admin
def admin_dashboard():
    db = get_db()
    memberships = db.execute(
        "SELECT * FROM membership_applications ORDER BY id DESC"
    ).fetchall()
    inquiries = db.execute(
        "SELECT * FROM contact_inquiries ORDER BY id DESC"
    ).fetchall()
    return render_template_string(ADMIN_TEMPLATE, memberships=memberships, inquiries=inquiries)


# Runs whether the app is started with "python app.py" (local dev)
# or imported by gunicorn on Render — the database must exist either way.
init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"FLEXIFIT server running — open http://localhost:{port}")
    print(f"Admin dashboard: http://localhost:{port}/admin  (user: admin, password: {ADMIN_PASSWORD})")
    app.run(host="0.0.0.0", port=port, debug=True)
