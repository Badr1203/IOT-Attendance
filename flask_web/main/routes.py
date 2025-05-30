from flask import Blueprint, render_template, session, redirect,  url_for

main_bp = Blueprint("main", __name__, template_folder="../templates")

@main_bp.route("/main")
def main_menu():
    if not session.get("logged_in"):
        return redirect("/login")
    return render_template("main.html")
@main_bp.route('/')
def index():
    return redirect(url_for('auth.login'))
