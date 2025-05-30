import os
import mysql.connector
from flask import Blueprint, render_template, session, redirect, request, url_for, flash

timetable_bp = Blueprint("timetable", __name__, template_folder="../templates")

@timetable_bp.route("/timetable", methods=["GET", "POST"])
def timetable():
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

    if request.method == "POST":
        room = request.form["room"]
        day = request.form["day"]
        start = request.form["start"] + ":00"
        end = request.form["end"] + ":00"
        subject = request.form["subject"]
        if (start > end):
            flash('Provide correct start and end time.', 'error')
            return redirect(url_for('timetable.timetable'))

        cursor.execute(
            "SELECT * FROM timetable WHERE room = %s AND day_of_week = %s AND start_time <= %s AND end_time > %s",
            (room, day, start, start),
        )

        existing = cursor.fetchone()

        if existing:
            flash('Timetable Conflict', 'error')
            conn.close()
            return redirect(url_for('timetable.timetable'))

        cursor.execute(
            "INSERT INTO timetable (room, day_of_week, start_time, end_time, subject) VALUES (%s, %s, %s, %s, %s)",
            (room, day, start, end, subject),
        )
        conn.commit()
        flash('Timetable entry added successfully!', 'success')

    cursor.execute("SELECT * FROM timetable ORDER BY day_of_week, start_time")
    rows = cursor.fetchall()
    conn.close()
    return render_template("timetable.html", timetable=rows)
