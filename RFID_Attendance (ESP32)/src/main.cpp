#include <Arduino.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <SPI.h>
#include <MFRC522.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <NTPClient.h>
#include <PubSubClient.h>

// LCD setup.
#define I2C_ADDRESS 0x27 // Change this if your LCD uses 0x3F or another address
#define SDA 21
#define SCL 22
#define SCROLL_DELAY 200

// RFID setup.
#define RST_PIN 4 // RST pin connected to GPIO22
#define SS_PIN 5   // SDA (SS) connected to GPIO5

// ESP32 Macros.
#define MONITOR_SPEED 115200
#define LED 2
#define LED_BLINK_SPEED 200
#define UTC_PLUS_5 18000
#define RETRIES 3
#define TIMEOUT 10000

// Wifi credentials.
const char *wifi_ssid = "Galaxy A11";
const char *wifi_password = "11223344";
const String macAddress = WiFi.macAddress();

// MQtt broker credentials.
const char *mqtt_server = "34.134.142.148";
const int mqtt_port = 1883;
const char *mqtt_username = "testVM";
const char *mqtt_password = "1122";
const char *mqtt_access = "rfid/access";

// Function declarations.
void wifiSetup();
void lcdSetup();
void reconnectMQTT();
void callback(char *topic, byte *payload, unsigned int length);
void print_lcd(String message, int row);
void print_lcd(String msg1, String msg2);
void blinkLED();
int parseTime(String timeStr);
void checkConnections();
bool publishWithRetry(String uid, String timestamp);

WiFiClient espClient;
PubSubClient client(espClient);
WiFiUDP ntpUDP;
LiquidCrystal_I2C lcd(I2C_ADDRESS, 16, 2);
MFRC522 rfid(SS_PIN, RST_PIN);
NTPClient timeClient(ntpUDP, "pool.ntp.org", UTC_PLUS_5, 60000); // UTC time, update every 60s

enum State {
  READING,
  WAITING_FOR_SERVER
};

enum Lesson_State {
  NO_LESSON,
  WATING_FOR_LESSON,
  LESSON
};

State currentState = READING;
Lesson_State lessonState = NO_LESSON;

String lastUID = "";
unsigned long lastReadTime = 0;
unsigned long cooldown = 3000;  // milliseconds (3 seconds)

void setup()
{
  Serial.begin(MONITOR_SPEED);
  Wire.begin(SDA, SCL); // Set I2C pins for ESP32
  pinMode(LED, OUTPUT);
  digitalWrite(LED, HIGH);

  lcdSetup();
  wifiSetup();

  // RFID setup
  SPI.begin();     // Start SPI bus
  rfid.PCD_Init(); // Init RFID reader
  print_lcd("RFID Reader Initialized.", 0);

  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
  client.setKeepAlive(30); 

  timeClient.begin();
  if (!timeClient.update()) Serial.println("LOG: setup: timeClient.update() fail"); // Get initial time
  delay(100);
  String time = timeClient.getFormattedTime();
  Serial.print("LOG: setup: Time is ");
  Serial.print(time); 
  Serial.println("LOG: Exiting setup");

}

void loop()
{
  checkConnections();

  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) {
    return; // No card detected
  }

  client.loop();

  // Read UID
  String uid = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    uid += String(rfid.uid.uidByte[i], HEX);
    if (i < rfid.uid.size - 1) uid += ":";
  }

  String timestamp = timeClient.getFormattedTime();
  Serial.print("UID: ");
  Serial.println(uid);
  Serial.print("Time: ");
  Serial.println(timestamp);

  // Avoid repeatedly publishing the same uid.
  unsigned long time_now = millis();
  if (uid != lastUID && (time_now - lastReadTime) > cooldown) {
    lastUID = uid;
    lastReadTime = time_now;

    publishWithRetry(uid, timestamp);
  }
  else {
    if (lessonState != NO_LESSON)print_lcd("  You    have  ","already Logged.");
  } 

  rfid.PICC_HaltA();       // Stop reading
  rfid.PCD_StopCrypto1();  // Stop encryption
  delay(2000);             // Small delay before next read
}
// Function definitions

bool publishWithRetry(String uid, String timestamp) {
  int attempt;
  String payload = "{\"uid\":\"" + uid + "\",\"timestamp\":\"" + timestamp +  "\",\"MAC_Address\":\"" + macAddress + "\"}";
  Serial.print("Publishing: ");
  Serial.println(payload);

  for (attempt = 1; attempt <= RETRIES; attempt++) {
    currentState = WAITING_FOR_SERVER;
    client.publish(mqtt_access, payload.c_str());

    Serial.print("Waiting for server... Attempt ");
    print_lcd("Connecting to server", 0);
    Serial.println(attempt);
    
    unsigned long start = millis();
    while (millis() - start < TIMEOUT) {
      checkConnections();
      client.loop();

      if (currentState == READING) {
        Serial.println("Server responded!");
        for (int i = 1; i < attempt; i++) {
          Serial.print("Printing redundent messages: ");
          Serial.println(i);
          client.loop();
          delay(100);
        }
        Serial.println("LOG: Printed redundent messages");
        return true;
      }

      delay(100);
    }

    Serial.println("Timeout, retrying...");
  }

  // After retries, failed to get a response
  print_lcd("No response from", "server.");
  for (int i = 1; i < attempt; i++) {
          Serial.print("Printing redundent messages: ");
          Serial.println(i);
          client.loop();
          delay(100);
        }
  return false;
}


// Parses time String "HH:MM:SS" to int seconds
// @return int seconds
int parseTime(String timeStr)
{
  int hour = timeStr.substring(0, 2).toInt();
  int minute = timeStr.substring(3, 5).toInt();
  int second = timeStr.substring(6, 8).toInt();

  int now = hour * 3600 + minute * 60 + second;

  return now;
}

void wifiSetup()
{
  delay(100);
  WiFi.mode(WIFI_STA);
  WiFi.begin(wifi_ssid, wifi_password);
  print_lcd("Connecting to", 0);

  // Wait until connected
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED)
  {
    delay(500);
    Serial.print(".");
    lcd.print(".");
    attempts++;
    if (attempts > 20)
    {
      print_lcd("Failed to connect to WiFi.", 0);
      return;
    }
  }

  String ip = "IP address: " + WiFi.localIP().toString();
  print_lcd("WiFi connected!", ip);
}

void lcdSetup()
{
  while (true)
  {
    Wire.beginTransmission(I2C_ADDRESS);
    if (Wire.endTransmission() == 0)
    {
      Serial.println("LCD detected!");
      break;
    }
    Serial.println("Waiting for LCD...");
    delay(1000); // Check every 1 second
  }
  delay(500);

  lcd.init();
  lcd.backlight();
  print_lcd("LCD Connected!", 0);
}

void print_lcd(String message, int row)
{
  int scrollIndex = 0;
  if (row == 0)
    lcd.clear();
  Serial.println(message);

  if (message.length() > 16)
  {
    // Scroll message
    do
    {
      String displayText = message.substring(scrollIndex, scrollIndex + 16);
      scrollIndex++;
      lcd.setCursor(0, row);
      lcd.print(displayText);
      delay(SCROLL_DELAY);
    } while (scrollIndex <= message.length() - 16);
  }
  else
  {
    lcd.setCursor(0, row);
    lcd.print(message);
  }
  delay(500);
}

void print_lcd(String msg1, String msg2)
{
  print_lcd(msg1, 0);
  print_lcd(msg2, 1);
}

//Blink LED
void blinkLED() {
  Serial.println("Making Gesture");
  for (int i = 0; i < 10; i++)
  {
    digitalWrite(LED, LOW);
    delay(LED_BLINK_SPEED);
    digitalWrite(LED, HIGH);
    delay(LED_BLINK_SPEED);
  }
}

void checkConnections() {
  delay(100);
  //check wifi connection.
  if (WiFi.status() != WL_CONNECTED) {
    print_lcd("WiFi disconnected.", "Trying to reconnect...");
    wifiSetup();
  }

  // check MQTT connection.
  if (!client.connected()) {
    reconnectMQTT();
    client.loop();
  }
}

void callback(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  Serial.print("[MQTT] Received on ");
  Serial.print(topic);
  Serial.print(": ");
  Serial.println(message);
  
  if (message == "NOT_REGISTERED") {
    print_lcd("Not Registered", 0);
  } else if (message == "DUBLICATE") {
    Serial.println(message);
    print_lcd("  You    have  ","already Logged.");
  } else if (message == "NO_LESSON") {
    print_lcd("No lessons today.", 0);
    lessonState = NO_LESSON;
  } else if (message == "UNKNOWN") {
    print_lcd("Device is not", "   registered");
  } else {
    print_lcd("Welcome, " + message, 0);
    lessonState = LESSON;
  }

  currentState = READING;
}

void reconnectMQTT() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect("ESP32Client", mqtt_username, mqtt_password)) {
      Serial.println("connected");
      Serial.print("Subscribed to: ");
      String subscription = mqtt_access;
      subscription += "/";
      subscription += macAddress;
      Serial.println(subscription);
      client.subscribe(subscription.c_str());
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" trying again in 5 seconds");
      delay(5000);
    }
  }
}
