import processing.serial.*;
import java.awt.Toolkit;

Serial myPort;
int currentAngle = 0;
int currentDistance = 400;
float maxRange = 150.0;
float alertDistance = 30.0;
String connectedPort = "Searching...";

float[] scanMap = new float[181];
int[] pointLife = new int[181];
long lastBeepTime = 0;

void setup() {
  size(1200, 650);
  
  for (int i = 0; i <= 180; i++) {
    scanMap[i] = 400;
    pointLife[i] = 0;
  }

  // اكتشاف منفذ الأردوينو المتصل تلقائياً
  String[] ports = Serial.list();
  printArray(ports);
  
  if (ports.length > 0) {
    // يختار آخر منفذ متاح (عادةً هو الأردوينو)
    connectedPort = ports[ports.length - 1];
    try {
      myPort = new Serial(this, connectedPort, 115200);
      myPort.clear();
      myPort.bufferUntil('\n');
    } catch (Exception e) {
      connectedPort = "Port Busy! Close Arduino IDE";
    }
  } else {
    connectedPort = "No Arduino Found";
  }
}

void draw() {
  background(8, 13, 22);

  float radarCenterX = 430;
  float radarCenterY = 560;
  float maxRadius = 380;

  drawDashboardFrame();
  drawRadarGrid(radarCenterX, radarCenterY, maxRadius);
  drawDetectedPoints(radarCenterX, radarCenterY, maxRadius);
  drawSweepBeam(radarCenterX, radarCenterY, maxRadius);
  drawSidePanel();
}

void serialEvent(Serial p) {
  try {
    String incomingData = p.readStringUntil('\n');
    if (incomingData != null) {
      incomingData = trim(incomingData);
      String[] parts = split(incomingData, ',');
      if (parts.length == 2) {
        int ang = constrain(int(parts[0]), 0, 180);
        int dist = int(parts[1]);
        
        currentAngle = ang;
        currentDistance = dist;

        if (dist > 0 && dist <= maxRange) {
          scanMap[ang] = dist;
          pointLife[ang] = 255;
        } else {
          scanMap[ang] = 400;
          pointLife[ang] = 0;
        }
      }
    }
  } catch (Exception e) {}
}

void drawDashboardFrame() {
  fill(14, 22, 36);
  noStroke();
  rect(0, 0, width, 55);
  
  stroke(0, 210, 255, 80);
  strokeWeight(1);
  line(0, 55, width, 55);

  fill(0, 225, 255);
  textSize(22);
  textAlign(LEFT, CENTER);
  text("ULTRASONIC TACTICAL RADAR // SYSTEM MONITOR", 25, 27);

  fill(120, 160, 190);
  textSize(14);
  textAlign(RIGHT, CENTER);
  text("PORT: " + connectedPort + " | BAUD: 115200 | RANGE: " + int(maxRange) + " CM", width - 25, 27);
}

void drawRadarGrid(float cx, float cy, float maxR) {
  pushMatrix();
  translate(cx, cy);
  
  noFill();
  strokeWeight(1.5);
  for (int i = 1; i <= 4; i++) {
    float r = (maxR / 4.0) * i;
    stroke(0, 200, 255, i == 4 ? 140 : 60);
    arc(0, 0, r * 2, r * 2, PI, TWO_PI);
    
    fill(0, 200, 255, 180);
    textSize(13);
    textAlign(LEFT, BOTTOM);
    text(int((maxRange / 4.0) * i) + "cm", r + 5, -4);
    noFill();
  }

  line(-maxR - 15, 0, maxR + 15, 0);
  for (int a = 30; a <= 150; a += 30) {
    float rad = radians(a);
    stroke(0, 200, 255, 50);
    line(0, 0, maxR * cos(rad), -maxR * sin(rad));
    
    fill(140, 190, 220);
    textSize(13);
    textAlign(CENTER, CENTER);
    text(a + "°", (maxR + 22) * cos(rad), -(maxR + 22) * sin(rad));
  }
  popMatrix();
}

void drawSweepBeam(float cx, float cy, float maxR) {
  pushMatrix();
  translate(cx, cy);
  float rad = radians(currentAngle);

  for (int i = 0; i < 15; i++) {
    float trailRad = radians(constrain(currentAngle - i, 0, 180));
    stroke(0, 230, 255, map(i, 0, 15, 70, 0));
    strokeWeight(3);
    line(0, 0, maxR * cos(trailRad), -maxR * sin(trailRad));
  }

  stroke(150, 255, 255);
  strokeWeight(3);
  line(0, 0, maxR * cos(rad), -maxR * sin(rad));
  
  fill(0, 230, 255);
  noStroke();
  ellipse(0, 0, 14, 14);
  popMatrix();
}

void drawDetectedPoints(float cx, float cy, float maxR) {
  pushMatrix();
  translate(cx, cy);
  
  for (int a = 0; a <= 180; a++) {
    if (pointLife[a] > 0 && scanMap[a] <= maxRange) {
      float pixDist = (scanMap[a] / maxRange) * maxR;
      float rad = radians(a);
      float x = pixDist * cos(rad);
      float y = -pixDist * sin(rad);

      boolean isDanger = (scanMap[a] <= alertDistance);
      
      noStroke();
      if (isDanger) {
        fill(255, 45, 75, pointLife[a] * 0.35);
      } else {
        fill(255, 180, 0, pointLife[a] * 0.35);
      }
      ellipse(x, y, 18, 18);

      if (isDanger) {
        fill(255, 60, 90, pointLife[a]);
      } else {
        fill(255, 210, 50, pointLife[a]);
      }
      ellipse(x, y, 8, 8);

      pointLife[a] = max(0, pointLife[a] - 2);
    }
  }
  popMatrix();
}

void drawSidePanel() {
  float panelX = 860;
  float panelW = 315;
  
  fill(14, 22, 36);
  stroke(0, 210, 255, 70);
  strokeWeight(1.5);
  rect(panelX, 80, panelW, 540, 12);

  boolean isAlert = (currentDistance > 0 && currentDistance <= alertDistance);
  boolean isDetected = (currentDistance > 0 && currentDistance <= maxRange);

  if (isAlert) {
    fill(180, 20, 45);
    stroke(255, 70, 90);
    if (millis() - lastBeepTime > 400) {
      Toolkit.getDefaultToolkit().beep();
      lastBeepTime = millis();
    }
  } else if (isDetected) {
    fill(20, 60, 85);
    stroke(0, 210, 255);
  } else {
    fill(18, 32, 48);
    stroke(60, 100, 130);
  }
  rect(panelX + 20, 105, panelW - 40, 85, 8);

  fill(255);
  textAlign(CENTER, CENTER);
  textSize(14);
  text("SYSTEM STATUS", panelX + panelW / 2, 128);
  textSize(22);
  String statusText = isAlert ? "PROXIMITY ALERT!" : (isDetected ? "TARGET LOCKED" : "AREA CLEAR");
  text(statusText, panelX + panelW / 2, 160);

  drawMetricBox(panelX + 20, 215, panelW - 40, 110, "SCAN ANGLE", currentAngle + "°", float(currentAngle) / 180.0, color(0, 220, 255));

  String distLabel = isDetected ? currentDistance + " cm" : "---";
  float distRatio = isDetected ? constrain(currentDistance / maxRange, 0, 1) : 0;
  color barCol = isAlert ? color(255, 60, 90) : color(255, 200, 40);
  drawMetricBox(panelX + 20, 345, panelW - 40, 110, "TARGET DISTANCE", distLabel, distRatio, barCol);

  fill(140, 180, 210);
  textAlign(LEFT, CENTER);
  textSize(13);
  
  fill(255, 60, 90);
  ellipse(panelX + 35, 495, 10, 10);
  fill(200, 220, 240);
  text("Danger Zone (< " + int(alertDistance) + " cm)", panelX + 52, 495);

  fill(255, 210, 50);
  ellipse(panelX + 35, 525, 10, 10);
  fill(200, 220, 240);
  text("Detected Object (30 - " + int(maxRange) + " cm)", panelX + 52, 525);

  fill(0, 220, 255);
  ellipse(panelX + 35, 555, 10, 10);
  fill(200, 220, 240);
  text("Active Radar Beam", panelX + 52, 555);
}

void drawMetricBox(float x, float y, float w, float h, String title, String value, float progress, color barColor) {
  fill(10, 16, 28);
  stroke(0, 200, 255, 50);
  strokeWeight(1);
  rect(x, y, w, h, 8);

  fill(130, 175, 205);
  textAlign(LEFT, TOP);
  textSize(13);
  text(title, x + 15, y + 14);

  fill(255);
  textSize(30);
  text(value, x + 15, y + 36);

  fill(25, 38, 56);
  noStroke();
  rect(x + 15, y + h - 22, w - 30, 8, 4);

  fill(barColor);
  rect(x + 15, y + h - 22, (w - 30) * progress, 8, 4);
}
