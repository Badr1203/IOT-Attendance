from flask import Blueprint, render_template, session, redirect, url_for, request
import mysql.connector
from functools import wraps

logs_bp = Blueprint("logs", __name__, template_folder="../templates")

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return wrapper

@logs_bp.route("/logs")
@login_required
def logs():
    if not session.get("logged_in"):
        return redirect("/login")

    db = mysql.connector.connect(
        host="34.134.142.148",
        user="mqttuser",
        password="1001#testVM1122",
        database="rfid_attendance"
    )
    cursor = db.cursor(dictionary=True)

    date = request.args.get('date')
    room = request.args.get('room')

    query = "SELECT * FROM logs"
    filters = []
    values = []

    if date:
        filters.append("date = %s")
        values.append(date)
    if room:
        filters.append("room = %s")
        values.append(room)

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += " ORDER BY id DESC"
    cursor.execute(query, values)
    logs = cursor.fetchall()

    # Get unique room names for dropdown
    cursor.execute("SELECT DISTINCT room FROM logs")
    rooms = [row['room'] for row in cursor.fetchall()]

    db.close()
    return render_template("logs.html", logs=logs, rooms=rooms)
