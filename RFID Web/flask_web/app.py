from flask import Flask
import os
from auth.routes import auth_bp
from main.routes import main_bp
from logs.routes import logs_bp
from register_rfid.routes import register_rfid_bp
from timetable.routes import timetable_bp
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key'),

app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)
app.register_blueprint(logs_bp)
app.register_blueprint(timetable_bp)
app.register_blueprint(register_rfid_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
