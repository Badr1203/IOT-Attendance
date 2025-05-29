import json
import mysql.connector
import paho.mqtt.client as mqtt
from datetime import datetime, date, time

# DB Config
db = mysql.connector.connect(
    host="34.134.142.148",
    user="mqttuser",
    password="1001#testVM1122",
    database="rfid_attendance"
)
cursor = db.cursor(dictionary=True)
print("LOG: Connected to a database")

# MQTT Config
MQTT_BROKER = "34.134.142.148"  # or your VM IP
MQTT_PORT = 1883
MQTT_ACCESS_TOPIC = "rfid/access"
MQTT_LOG_PYTHON = "rfid/log/python"

client = mqtt.Client()

# --- HANDLERS --- #

# Access log handler
def handle_access_log(data):
    try:
        uid = data['uid']
        timestamp = data['timestamp'] # Expecting ISO format: "09:00:00"
        MAC_address = data['MAC_Address']
        tmp_mac = MAC_address.strip().upper()

        today = date.today()
        date_str = today.isoformat()
        print("LOG: handle_access_log: Timestamp is <" + timestamp + ">")
        print("LOG: handle_access_log: uid is <" + uid + ">")
        print("LOG: handle_access_log: MAC is <" + MAC_address + ">")

        # Get room info
        ensure_db_connection()
        cursor.execute("SELECT room_name FROM device_rooms WHERE mac_address = %s", (tmp_mac,))
        result = cursor.fetchone()
        if result:
            room = result['room_name']
            print(f"[INFO] MAC {MAC_address} → Room {room}")

            # Confirm student exists
            ensure_db_connection()
            cursor.execute("SELECT name FROM students WHERE uid = %s", (uid,))
            student = cursor.fetchone()
            if student:
                student_name = student['name']
                client.publish(MQTT_LOG_PYTHON, "Student found.")
                print(f"[INFO] Student found: {student_name} ({uid}) for")

                # Current day and time
                now = datetime.now()
                current_day = now.strftime("%A")
                current_time = now.time()

                print(f"[INFO] {current_day}, {room}, {current_time}")

                # Query for ongoing or upcoming lessons
                query = """
                    SELECT room_name, subject, time_start, time_end
                    FROM timetable
                    WHERE day_of_week = %s AND room_name = %s AND time_end >= %s
                    ORDER BY time_start
                    LIMIT 1
                """

                # Check for lessons
                print(f"[INFO] {current_day}, {room}, {current_time}")
                ensure_db_connection()
                cursor.execute(query, (current_day, room, current_time))
                lesson = cursor.fetchone()
                print("[INFO] Check lesson: query executed.")
                if lesson:
                    subject = lesson['subject']
                    publish_message = json.dumps(result, default=str, indent=4)
                    client.publish(MQTT_LOG_PYTHON, "Lesson Found: " + publish_message)
                    print("[info] Lesson found")

                    # Check duplicate
                    ensure_db_connection()
                    cursor.execute("""
                        SELECT 1 FROM attendance_logs
                        WHERE uid = %s AND subject = %s AND date = %s
                        LIMIT 1
                    """, (uid, subject, date_str))
                    if cursor.fetchone():
                        print(f"[INFO] Duplicate log ignored: {uid} on {date_str} for {subject}")
                        client.publish(MQTT_ACCESS_TOPIC + "/" + MAC_address,"DUBLICATE")
                        return
                    else:
                        # Save log
                        cursor.execute("""
                            INSERT INTO attendance_logs (uid, student_name, subject, room_name, date, time)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (uid, student_name, subject, room, date_str, current_time))  # Optional: use room if known
                        db.commit()
                        client.publish(MQTT_ACCESS_TOPIC + "/" + MAC_address, student_name)
                else:
                    print(f"[WARN] No lessons: {room}")
                    client.publish(MQTT_ACCESS_TOPIC + "/" + MAC_address, "NO_LESSON")
            else:
                print(f"[WARN] UID not registered: {uid}")
                client.publish(MQTT_LOG_PYTHON, "UID not registered. Publisihin to" + MQTT_ACCESS_TOPIC + "/" + room)
                client.publish(MQTT_ACCESS_TOPIC + "/" + MAC_address, "NOT_REGISTERED")
        else:
            print(f"[WARN] Unknown MAC: {MAC_address}")
            client.publish(MQTT_LOG_PYTHON, "Unknow MAC. Publisihin to" + MQTT_ACCESS_TOPIC + "/" + room)
            client.publish(MQTT_ACCESS_TOPIC + "/" + MAC_address, "UNKNOWN")
    except Exception as e:
        print(f"[ERROR] Bad access log data: {data} — {e}")

# --- MQTT CALLBACKS --- #

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker")
    client.publish(MQTT_LOG_PYTHON, "Python script connected to broker. Publishing to " + MQTT_ACCESS_TOPIC)
    client.subscribe(MQTT_ACCESS_TOPIC)

def on_message(client, userdata, msg):
    print("[MQTT] Message received.")
    topic = msg.topic
    payload = msg.payload.decode()
    client.publish(MQTT_LOG_PYTHON, "Message received. Topic is: ")
    client.publish(MQTT_LOG_PYTHON, topic)
    client.publish(MQTT_LOG_PYTHON, payload)

    if topic == MQTT_ACCESS_TOPIC:
        try:
            data = json.loads(payload)
            handle_access_log(data)
        except json.JSONDecodeError:
            print("[ERROR] Invalid JSON on rfid/access")
def ensure_db_connection():
    global db, cursor
    try:
        db.ping(reconnect=True, attempts=3, delay=2)
    except Exception as e:
        print(f"[ERROR] DB ping failed: {e}")
    cursor = db.cursor(dictionary=True)

# --- START MQTT --- #
client.username_pw_set(username="testVM", password="1122")
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT)
client.loop_forever()

