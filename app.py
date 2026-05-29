from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import sqlite3
import requests
import pytz
import atexit
import os

app = Flask(__name__)

DB_PATH = os.environ.get("DB_PATH", "medicaciones.db")
TIMEZONE = pytz.timezone("America/Argentina/Buenos_Aires")

MEDICATIONS = [
    {
        "id": "gota_dolor",
        "name": "Gota Dolor",
        "description": "Gota para el dolor",
        "interval_hours": 12,
        "color": "#e07b54",
        "icon": "💊",
    },
    {
        "id": "tratamiento_crema",
        "name": "Tratamiento + Crema",
        "description": "Gota Tratamiento y Crema (se aplican juntas)",
        "interval_hours": 8,
        "color": "#5b8dd9",
        "icon": "🩹",
    },
]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS applications (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            med_id  TEXT    NOT NULL,
            applied_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS config (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()


def get_last_application(med_id):
    conn = get_db()
    row = conn.execute(
        "SELECT applied_at FROM applications WHERE med_id=? ORDER BY applied_at DESC LIMIT 1",
        (med_id,),
    ).fetchone()
    conn.close()
    if row:
        dt = datetime.fromisoformat(row["applied_at"])
        if dt.tzinfo is None:
            dt = TIMEZONE.localize(dt)
        return dt
    return None


def get_config():
    conn = get_db()
    rows = conn.execute("SELECT key, value FROM config").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}


def send_whatsapp(message):
    cfg = get_config()
    phone = cfg.get("whatsapp_phone")
    apikey = cfg.get("callmebot_apikey")
    if not phone or not apikey:
        return False
    try:
        url = (
            f"https://api.callmebot.com/whatsapp.php"
            f"?phone={phone}&text={requests.utils.quote(message)}&apikey={apikey}"
        )
        r = requests.get(url, timeout=10)
        return r.status_code == 200
    except Exception:
        return False


def check_reminders():
    now = datetime.now(TIMEZONE)
    for med in MEDICATIONS:
        last = get_last_application(med["id"])
        if last is None:
            continue
        next_due = last + timedelta(hours=med["interval_hours"])
        diff = (now - next_due).total_seconds()
        if 0 <= diff <= 60:
            msg = (
                f"🐾 ¡Hora de la medicación de tu perrita!\n"
                f"{med['icon']} {med['name']} - cada {med['interval_hours']}hs\n"
                f"Última aplicación: {last.strftime('%H:%M')}"
            )
            send_whatsapp(msg)


init_db()
scheduler = BackgroundScheduler(timezone=TIMEZONE)
scheduler.add_job(check_reminders, "interval", minutes=1)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())


# ── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    now = datetime.now(TIMEZONE)
    result = []
    for med in MEDICATIONS:
        last = get_last_application(med["id"])
        if last:
            next_due = last + timedelta(hours=med["interval_hours"])
            remaining = (next_due - now).total_seconds()
            entry = {
                **med,
                "last_applied": last.isoformat(),
                "next_due": next_due.isoformat(),
                "remaining_seconds": int(remaining),
                "is_overdue": remaining < 0,
            }
        else:
            entry = {
                **med,
                "last_applied": None,
                "next_due": None,
                "remaining_seconds": None,
                "is_overdue": False,
            }
        result.append(entry)
    return jsonify(result)


@app.route("/api/apply", methods=["POST"])
def api_apply():
    data = request.get_json()
    med_id = data.get("med_id")
    applied_at_str = data.get("applied_at")

    if not med_id:
        return jsonify({"error": "med_id requerido"}), 400

    if applied_at_str:
        applied_at = datetime.fromisoformat(applied_at_str)
        if applied_at.tzinfo is None:
            applied_at = TIMEZONE.localize(applied_at)
    else:
        applied_at = datetime.now(TIMEZONE)

    conn = get_db()
    conn.execute(
        "INSERT INTO applications (med_id, applied_at) VALUES (?, ?)",
        (med_id, applied_at.isoformat()),
    )
    conn.commit()
    conn.close()
    return jsonify({"success": True, "applied_at": applied_at.isoformat()})


@app.route("/api/history/<med_id>")
def api_history(med_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT id, applied_at FROM applications WHERE med_id=? ORDER BY applied_at DESC LIMIT 30",
        (med_id,),
    ).fetchall()
    conn.close()
    return jsonify([{"id": r["id"], "applied_at": r["applied_at"]} for r in rows])


@app.route("/api/delete/<int:record_id>", methods=["DELETE"])
def api_delete(record_id):
    conn = get_db()
    conn.execute("DELETE FROM applications WHERE id=?", (record_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    if request.method == "POST":
        data = request.get_json()
        conn = get_db()
        for key, value in data.items():
            conn.execute(
                "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, value)
            )
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    else:
        cfg = get_config()
        return jsonify({
            "whatsapp_phone": cfg.get("whatsapp_phone", ""),
            "has_apikey": bool(cfg.get("callmebot_apikey")),
        })


@app.route("/api/test-whatsapp", methods=["POST"])
def api_test_whatsapp():
    ok = send_whatsapp("🐾 ¡Hola! Los recordatorios de medicación de tu perrita están activos.")
    return jsonify({"success": ok})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
