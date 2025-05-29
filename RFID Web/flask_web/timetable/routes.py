from flask import Blueprint, render_template, session, redirect, request, url_for, flash
import mysql.connector

timetable_bp = Blueprint("timetable", __name__, template_folder="../templates")

@timetable_bp.route("/timetable", methods=["GET", "POST"])
def timetable():
    if not session.get("logged_in"):
        return redirect("/login")

    db = mysql.connector.connect(
        host="34.134.142.148",
        user="mqttuser",
        password="1001#testVM1122",
        database="rfid_attendance"
    )
    cursor = db.cursor(dictionary=True)

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
            "SELECT * FROM timetable WHERE room_name = %s AND day_of_week = %s AND time_start <= %s AND time_end > %s",
            (room, day, start, start),
        )

        existing = cursor.fetchone()

        if existing:
            flash('Timetable Conflict', 'error')
            db.close()
            return redirect(url_for('timetable.timetable'))

        cursor.execute(
            "INSERT INTO timetable (room_name, day_of_week, time_start, time_end, subject) VALUES (%s, %s, %s, %s, %s)",
            (room, day, start, end, subject),
        )
        db.commit()
        flash('Timetable entry added successfully!', 'success')

    cursor.execute("SELECT * FROM timetable ORDER BY day_of_week, time_start")
    rows = cursor.fetchall()
    db.close()
    return render_template("timetable.html", timetable=rows)
