#include <Servo.h>

const int trigPin = 10;
const int echoPin = 11;
const int servoPin = 9;

Servo radarServo;

void setup() {
  Serial.begin(115200); // سرعة نقل أعلى لاستجابة فورية مع الأجسام المتحركة
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  
  radarServo.attach(servoPin, 600, 2400);
  radarServo.write(0);
  delay(500);
}

void loop() {
  // مسح سريع من 0 إلى 180
  for (int angle = 0; angle <= 180; angle++) {
    radarServo.write(angle);
    delay(10); 
    int distance = getInstantDistance();
    sendData(angle, distance);
  }

  // عودة سريعة من 180 إلى 0
  for (int angle = 180; angle >= 0; angle--) {
    radarServo.write(angle);
    delay(10);
    int distance = getInstantDistance();
    sendData(angle, distance);
  }
}

// قراءة لحظية سريعة لمنع تشوه صورة الأجسام المتحركة
int getInstantDistance() {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  // مهلة 15000 ميكروثانية تغطي حتى 250 سم وتكفي تماماً لمدى 150 سم
  long duration = pulseIn(echoPin, HIGH, 15000);

  if (duration == 0) {
    return 400;
  }

  int distance = duration * 0.0343 / 2;

  // استبعاد القراءات القريبة جداً (أقل من 2 سم) والبعيدة جداً
  if (distance > 150 || distance < 2) {
    return 400;
  }

  return distance;
}

void sendData(int angle, int distance) {
  Serial.print(angle);
  Serial.print(",");
  Serial.println(distance);
}