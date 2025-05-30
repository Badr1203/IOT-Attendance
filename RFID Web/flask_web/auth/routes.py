import os
from flask import Blueprint, render_template, request, redirect, session

auth_bp = Blueprint("auth", __name__, template_folder="../templates")

# Login credentials
USERNAME = os.getenv("ADMIN_USERNAME")
PASSWORD = os.getenv("ADMIN_PASSWORD")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == USERNAME and request.form["password"] == PASSWORD:
            session["logged_in"] = True
            return redirect("/main")
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/login")
