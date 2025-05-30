import threading
import os
import mysql.connector
from mysql.connector import Error
import paho.mqtt.client as mqtt
from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import datetime

register_rfid_bp = Blueprint('register_rfid', __name__, template_folder="../templates")

MQTT_BROKER = os.environ.get("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_USERNAME = os.environ.get("MQTT_USERNAME", "user")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD", "pass")
MQTT_TOPIC = "rfid/registration"

pending_uids = []

def on_message(client, userdata, msg):
    try:
        client.publish("rfid/log", "message received")
        payload = msg.payload.decode()
        uid, mac = payload.split(',')
        if not any(d['uid'] == uid for d in pending_uids):
            pending_uids.append({'uid': uid.strip(), 'mac': mac.strip()})
    except Exception as e:
        print("Error parsing message:", e)

def start_mqtt_listener():
    client = mqtt.Client()
    client.username_pw_set(username=MQTT_USERNAME, password=MQTT_PASSWORD)
    client.on_message = on_message
    print(MQTT_BROKER)
    client.connect(MQTT_BROKER, MQTT_PORT)
    client.subscribe(MQTT_TOPIC)
    client.loop_start()

threading.Thread(target=start_mqtt_listener, daemon=True).start()

@register_rfid_bp.route('/register_rfid')
def show_pending():
    return render_template('register_rfid.html', pending_uids=pending_uids)

@register_rfid_bp.route('/register_rfid/register', methods=['POST'])
def register_student():
    db_config ={
        'host': os.environ.get('DB_HOST', 'localhost'),
        'user': os.environ.get('DB_USER', 'root'),
        'password': os.environ.get('DB_PASSWORD', ''),
        'database': os.environ.get('DB_NAME', 'your_database_name')
    }
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    uid = request.form['uid']
    name = request.form['name']
    reg_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    print(uid.__len__())
    try:
        cursor.execute("INSERT INTO students (name, uid, reg_date) VALUES (%s, %s, %s)", (name, uid, reg_date))
        conn.commit()
    except Error as e:
        flash(f"Databas eror - {e}","success")
    pending_uids[:] = [d for d in pending_uids if d['uid'] != uid]
    return redirect(url_for('register_rfid.show_pending'))
