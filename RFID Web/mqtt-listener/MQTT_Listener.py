import json
import threading
import time as time_t
import mysql.connector
from mysql.connector import Error
import paho.mqtt.client as mqtt
from datetime import datetime, date, time

# MQTT Config
MQTT_BROKER = "34.134.142.148"  # or your VM IP
MQTT_PORT = 1883
MQTT_ACCESS_TOPIC = "rfid/access"
MQTT_LOG_PYTHON = "rfid/log/python"
MQTT_USERNAME = "testVM"
MQTT_PASSWORD = "1122"

# DB Config
db_config ={
    'host':'34.134.142.148',
    'user':'mqttuser',
    'password': '1001#testVM1122',
    'database':'rfid_attendance'
}
conn = mysql.connector.connect(**db_config)
cursor = conn.cursor(dictionary=True)
print("LOG: Connected to a database")

client = mqtt.Client()

def identify_device(mac_address) -> str:
    ensure_db_connection()
    cursor.execute("SELECT room FROM device_rooms WHERE mac_address = %s", (mac_address,))
    result = cursor.fetchone()
    if result: return result
    else:
        print(f"[WARN] Unknown MAC: {mac_address}")
        return ""

# Get ongoing lesson subject
#@return ongoing lesson
def identify_subject(room) -> str:
    # Current day and time
    now = datetime.now()
    current_day = now.strftime("%A")
    current_time = now.time().replace(microsecond=0)
    print(f"[INFO] {current_day}, {room}, {current_time}")

    # Query for ongoing  lessons
    query = """
        SELECT id, subject
        FROM timetable
        WHERE day_of_week = %s AND room = %s AND start_time >= %s AND end_time <= %s
        ORDER BY start_time
        LIMIT 1
    """

    # Check for lessons
    ensure_db_connection()
    cursor.execute(query, (current_day, room, current_time, current_time))
    result = cursor.fetchone()
    if result: return result
    else:
        print(f"[WARN] No lessons: {room}")
        return ""
       
# Confirm student exists
def identify_student(uid) -> str:
    ensure_db_connection()
    cursor.execute("SELECT name FROM students WHERE uid = %s", (uid,))
    student = cursor.fetchone()
    if student: return student
    else:
        print(f"[WARN] UID not registered: {uid}")
        return ""

def is_logged(uid, lesson_id, subject, date) -> bool:
    try:
        ensure_db_connection()
        cursor.execute("""
            SELECT 1 FROM logs
            WHERE uid = %s AND lesson_id = %s AND date = %s
            LIMIT 1
        """, (uid, lesson_id, date))
        if cursor.fetchone(): return True
        else:
            print(f"[INFO] Duplicate log ignored: {uid} on {date} for {subject}") 
            return False
    except Error as err:
        if err.errno == 1452:
            print("Foreign key constraint failed.")
        elif err.errno == 1062:
            print("Duplicate entry.")
        else:
            print("Other database error:", err)
        return False
# --- HANDLERS --- #

# Access log handler
def handle_access_log(data):
    try:
        uid = data['uid']
        timestamp = data['timestamp'] # Expecting ISO format: "09:00:00"
        MAC_address = data['MAC_Address']

        print("LOG: handle_access_log: Timestamp is <" + timestamp + ">") #log
        print("LOG: handle_access_log: uid is <" + uid + ">") #log
        print("LOG: handle_access_log: MAC is <" + MAC_address + ">") #log

        today = date.today()
        date_str = today.isoformat()
        now = datetime.now()
        current_time = now.time().replace(microsecond=0)

        # Check Device
        print("LOG: check device") #log
        result = identify_device(MAC_address)
        if not result: 
            client.publish(MQTT_ACCESS_TOPIC + "/" + MAC_address, "UNKNOWN")
            return

        # Check lesson
        print("LOG: check lesson") #log
        room = result['room']
        result = identify_subject(room)
        if not result:
            print(f"[INFO] MAC {MAC_address} → Room {room}")
            client.publish(MQTT_ACCESS_TOPIC + "/" + MAC_address, "NO_LESSON")
            return
        
        # Check student
        print("LOG: check student") #log
        lesson_id = result['id']
        subject = result['subject']
        result = identify_student(uid)
        if not result:
            print(f"[INFO] Ongoing lesson: {subject}")
            client.publish(MQTT_ACCESS_TOPIC + "/" + MAC_address, "NOT_REGISTERED")
            return
        
        # Check Dublicate logs
        student = result['name']
        if is_logged(uid, lesson_id, subject, ):
            client.publish(MQTT_ACCESS_TOPIC + "/" + MAC_address,"DUBLICATE")
            return
        else:
            # Save log
            cursor.execute("""
                INSERT INTO logs (uid, lesson_id, room, date, time)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (uid, lesson_id, room, date_str, current_time))  # Optional: use room if known
            conn.commit()
            client.publish(MQTT_ACCESS_TOPIC + "/" + MAC_address, student)         
    except Exception as e:
        print(f"[ERROR] Bad access log data: {data} — {e}")

# --- MQTT CALLBACKS --- #

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker")
    client.subscribe(MQTT_ACCESS_TOPIC)

def on_message(client, userdata, msg):
    print("[MQTT] Message received.")
    topic = msg.topic
    payload = msg.payload.decode()

    if topic == MQTT_ACCESS_TOPIC:
        try:
            data = json.loads(payload)
            handle_access_log(data)
        except json.JSONDecodeError:
            print("[ERROR] Invalid JSON on rfid/access")

# Function to keep DB connection alive
def keep_db_alive(interval=300):  # 300 seconds = 5 minutes
    def ping():
        while True:
            try:
                cursor.execute("SELECT 1")  # lightweight ping
                # Optional: log this if needed
            except Exception as e:
                print("DB keep-alive failed, reconnecting...", e)
                reconnect()
            time_t.sleep(interval)
    
    # Run the ping in a separate background thread
    thread = threading.Thread(target=ping, daemon=True)
    thread.start()
def reconnect():
    global conn, cursor
    try:
        conn.close()
    except:
        pass
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
def ensure_db_connection():
    global conn, cursor
    try:
        conn.ping(reconnect=True, attempts=3, delay=2)
    except Exception as e:
        print(f"[ERROR] DB ping failed: {e}")
    cursor = conn.cursor(dictionary=True)

# --- START MQTT --- #
#keep_db_alive()
client.username_pw_set(username=MQTT_USERNAME, password=MQTT_PASSWORD)
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT)
client.loop_forever()
