# IoT-Based RFID Attendance System

This project is an **IoT-powered RFID attendance system** built with **ESP32**, **RFID-RC522**, and a **16x2 LCD** display. It uses **MQTT** for communication and a **Python Flask web server** to manage student data, view logs, and configure the timetable.

---

## 🚀 Project Overview

### Components

* **ESP32** microcontroller
* **RFID-RC522** card reader
* **16x2 LCD Display**
* **MQTT Broker (e.g., Mosquitto)**
* **Python server with Flask app**
* **MySQL database**
* **Dockerized server environment**

### How It Works

1. **ESP32** reads UID from RFID card and publishes it via **MQTT** (`rfid/access` topic).
2. **Python server** receives UID, checks against MySQL database:

   * Sends back `Hello, <Name>` if registered and lesson is ongoing
   * Sends `NO_LESSON` if outside lesson hours
   * Sends `NOT_REGISTERED` and publishes UID to `rfid/registration`
3. **Web interface** (Flask) allows users to:

   * View **attendance logs**
   * **Register** new UIDs when detected
   * View and manage the **lesson timetable**

---

## 📚 Features

* Real-time UID scanning and attendance logging
* MQTT-based communication between ESP32 and server
* Flask web interface for:

  * Viewing attendance logs by date and room
  * Managing timetable
  * Registering unknown UIDs
* Auto-reconnects for stable operation
* Time-based UID acceptance control

---

## 🪜 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/Badr1203/IOT-Attendance.git
cd IOT-Attendance
```

### 2. Setup `.env` File (Flask + Python Server)

Create a `.env` file in both flask_web and mqtt-listener directories or in root directory:

```ini
DB_HOST=localhost
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=rfid_attendance
MQTT_BROKER=your_broker_ip
MQTT_PORT=1883
MQTT_USERNAME=your_mqtt_username
MQTT_PASSWORD=your_mqtt_password
SECRET_KEY=your_flask_secret_key
```
> **Note:** Make sure `.env` is in `.gitignore` to avoid leaking credentials.

### 3. Setup `secrets.h` (ESP32 Firmware)

Create a file named `secrets.h` inside the ESP32 firmware directory:

```cpp
// secrets.h
#ifndef SECRETS_H
#define SECRETS_H

// WIFI credentials
const char *WIFI_SSID = "your_wifi_ssid";
const char *WIFI_PASSWORD = "your_wifi_password";

// MQTT credentials
const char *MQTT_SERVER = "your_broker_ip";
const int MQTT_PORT = 1883;
const char *MQTT_USERNAME = "your_mqtt_username";
const char *MQTT_PASSWORD = "your_mqtt_password";

#endif
```

> **Note:** Make sure `secrets.h` is in `.gitignore` to avoid leaking credentials.

---

## 🚧 Server Setup

### Option 1: Using Docker

#### 1. Build and Run

```bash
docker-compose up --build -d
```

#### 2. Services in Docker

* `main.py` MQTT + DB logic (Python)
* `web/` Flask app (runs on port 5000)

#### 3. Access Web Interface

```
http://<server-ip>:5000
```

---

## 📆 Folder Structure

```
IOT-Attendance/
├── ESP32_firmware/            # Arduino/PlatformIO code for ESP32
├── RFID Web/flask-web         # Flask web application 
├── RFID Web/mqtt-listener     # Python MQTT listener and DB handler
├── README.md                  # Project documentation
```

---

## 📝 Database Schema

* **students(id, name, uid, reg\_date)**
* **timetable(id, room, day\_of\_week, start\_time, end\_time, subject)**
* **logs(id, uid, lesson\_id, room, date, time)**
* **device\_rooms(mac\_address, room)**

---

## 🚨 MQTT Topics

| Topic                       | Direction    | Description                        |
| --------------------------- | ------------ | ---------------------------------- |
| `rfid/access`               | ESP → Server | UID scanned by ESP32 + MAC address |
| `rfid/access/<MAC_address>` | Server → ESP | Response: Hello, No Lessons, etc.  |
| `rfid/registration`         | ESP →    Web | Unknown UID notification           |

---

## 🎓 Future Improvements

* Admin authentication panel
* Export logs to CSV
* Add fingerprint or face recognition
* Mobile App for NFC/Bluetooth attendance
* Real-time dashboards for admin

---

## 🙏 Credits

Developed by **Badriddin Karimjonov**

> Feel free to fork, contribute, or raise issues!

---

## ⚒ Troubleshooting

* Make sure MQTT broker is running and accessible
* Ensure Flask and Python MQTT scripts use the correct `.env`
* ESP32 should be connected to WiFi with correct credentials
