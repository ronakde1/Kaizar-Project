// ─────────────────────────────────────────────────────────
//  Study Environment Monitor — Arduino Nano
//  Output: CSV over serial → distance_cm,temp_c,loud
//  Requires: "DHT sensor library" by Adafruit
// ─────────────────────────────────────────────────────────

#include <DHT.h>   // Adafruit DHT library

#define TRIG_PIN      7
#define ECHO_PIN      6
#define DHT_PIN       5
#define DHT_TYPE      DHT11
#define SOUND_PIN     8
#define BUZZER_PIN    10

const int PROX_CM     = 30;
const int TEMP_WARN_C = 28;

const unsigned long SENSOR_INTERVAL = 1000;
const unsigned long BUZZ_DURATION   = 150;
unsigned long lastRead  = 0;
unsigned long buzzUntil = 0;

DHT dht(DHT_PIN, DHT_TYPE);  // Adafruit constructor

void setup() {
  Serial.begin(9600);
  pinMode(TRIG_PIN,   OUTPUT);
  pinMode(ECHO_PIN,   INPUT);
  pinMode(SOUND_PIN,  INPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);
  dht.begin();  // Adafruit requires begin()

  Serial.println(F("distance_cm,temp_c,loud"));
}

void loop() {
  unsigned long now = millis();

  if (now >= buzzUntil) {
    digitalWrite(BUZZER_PIN, LOW);
  }

  if (now - lastRead >= SENSOR_INTERVAL) {
    lastRead = now;

    float distCm  = measureDistance();
    float tempC   = dht.readTemperature();  // Adafruit read
    bool  loud    = (digitalRead(SOUND_PIN) == HIGH);

    if (distCm > 0 && distCm <= PROX_CM) triggerBuzz(now);

    // ── CSV line: distance,temp,loud ─────────────────────
    Serial.print(distCm, 1);
    Serial.print(F(","));

    // -99 sentinel if DHT11 read fails
    if (isnan(tempC)) Serial.print(F("-99"));
    else              Serial.print(tempC, 1);
    Serial.print(F(","));

    Serial.println(loud ? 1 : 0);
  }
}

float measureDistance() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long duration = pulseIn(ECHO_PIN, HIGH, 30000);
  if (duration == 0) return -1.0;
  return duration * 0.01723;
}

void triggerBuzz(unsigned long now) {
  if (now >= buzzUntil) {
    digitalWrite(BUZZER_PIN, HIGH);
    buzzUntil = now + BUZZ_DURATION;
  }
}