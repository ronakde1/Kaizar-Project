#include <DHT.h>

#define TRIG_PIN      7
#define ECHO_PIN      6
#define DHT_PIN       5
#define DHT_TYPE      DHT11
#define SOUND_PIN     8
#define MOTOR_PIN     4
#define LED_PROX      9
#define LED_TEMP      2
#define LED_NOISE     3

const int PROX_CM     = 10;
const int TEMP_WARN_C = 28;

const unsigned long SENSOR_INTERVAL = 1000;
unsigned long lastRead = 0;

const int PULSE_ON    = 150;
const int PULSE_OFF   = 150;
const int PULSE_COUNT = 3;

struct Alert {
  int  pin;
  int  pin2;
  bool active;
  int  pulsesDone;
  bool pulseHigh;
  unsigned long pulseUntil;
};

Alert alertProx  = { LED_PROX,  MOTOR_PIN, false, 0, false, 0 };
Alert alertTemp  = { LED_TEMP,  -1,        false, 0, false, 0 };
Alert alertNoise = { LED_NOISE, -1,        false, 0, false, 0 };

DHT dht(DHT_PIN, DHT_TYPE);

void startAlert(Alert &a, unsigned long now);
void updateAlert(Alert &a, unsigned long now);
float measureDistance();

void pinWrite(Alert &a, int val) {
  digitalWrite(a.pin, val);
  if (a.pin2 != -1) digitalWrite(a.pin2, val == LOW ? HIGH : LOW);
}

void setup() {
  Serial.begin(9600);
  pinMode(TRIG_PIN,  OUTPUT);
  pinMode(ECHO_PIN,  INPUT);
  pinMode(SOUND_PIN, INPUT);
  pinMode(MOTOR_PIN, OUTPUT);
  pinMode(LED_PROX,  OUTPUT);
  pinMode(LED_TEMP,  OUTPUT);
  pinMode(LED_NOISE, OUTPUT);
  digitalWrite(MOTOR_PIN, LOW);
  digitalWrite(LED_PROX,  HIGH);
  digitalWrite(LED_TEMP,  HIGH);
  digitalWrite(LED_NOISE, HIGH);
  dht.begin();
  Serial.println(F("distance_cm,temp_c,loud"));
}

void loop() {
  unsigned long now = millis();

  while (Serial.available() > 0) {
    char cmd = Serial.read();
    if      (cmd == '1') digitalWrite(MOTOR_PIN, HIGH);
    else if (cmd == '0') digitalWrite(MOTOR_PIN, LOW);
  }

  updateAlert(alertProx,  now);
  updateAlert(alertTemp,  now);
  updateAlert(alertNoise, now);

  if (now - lastRead >= SENSOR_INTERVAL) {
    lastRead = now;

    float distCm = measureDistance();
    float tempC  = dht.readTemperature();
    bool  loud   = (digitalRead(SOUND_PIN) == HIGH);

    if (distCm > 0 && distCm <= PROX_CM)      startAlert(alertProx,  now);
    if (!isnan(tempC) && tempC >= TEMP_WARN_C) startAlert(alertTemp,  now);
    if (loud)                                  startAlert(alertNoise, now);

    Serial.print(distCm, 1);
    Serial.print(F(","));
    if (isnan(tempC)) Serial.print(F("-99"));
    else              Serial.print(tempC, 1);
    Serial.print(F(","));
    Serial.println(loud ? 1 : 0);
  }
}

void startAlert(Alert &a, unsigned long now) {
  if (a.active) return;
  a.active     = true;
  a.pulsesDone = 0;
  a.pulseHigh  = true;
  a.pulseUntil = now + PULSE_ON;
  digitalWrite(a.pin, LOW);
  if (a.pin2 != -1) digitalWrite(a.pin2, HIGH);
}

void updateAlert(Alert &a, unsigned long now) {
  if (!a.active) return;
  if (now < a.pulseUntil) return;

  if (a.pulseHigh) {
    digitalWrite(a.pin, HIGH);
    if (a.pin2 != -1) digitalWrite(a.pin2, LOW);
    a.pulsesDone++;
    if (a.pulsesDone >= PULSE_COUNT) {
      a.active = false;
      return;
    }
    a.pulseHigh  = false;
    a.pulseUntil = now + PULSE_OFF;
  } else {
    a.pulseHigh  = true;
    a.pulseUntil = now + PULSE_ON;
    digitalWrite(a.pin, LOW);
    if (a.pin2 != -1) digitalWrite(a.pin2, HIGH);
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