from flask import Flask
from auth.routes import auth_bp
from main.routes import main_bp
from logs.routes import logs_bp
from timetable.routes import timetable_bp

app = Flask(__name__)
app.secret_key = "your_secret_key"

app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)
app.register_blueprint(logs_bp)
app.register_blueprint(timetable_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
