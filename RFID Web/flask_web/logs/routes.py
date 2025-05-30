import os
import mysql.connector
from flask import Blueprint, render_template, session, redirect, url_for, request
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

    db_config ={
        'host': os.environ.get('DB_HOST', 'localhost'),
        'user': os.environ.get('DB_USER', 'root'),
        'password': os.environ.get('DB_PASSWORD', ''),
        'database': os.environ.get('DB_NAME', 'your_database_name')
    }
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

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

    conn.close()
    return render_template("logs.html", logs=logs, rooms=rooms)
