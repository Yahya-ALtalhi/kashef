import cv2
import serial
import serial.tools.list_ports
import threading
import time
import math
import numpy as np
from ultralytics import YOLO

# --- إعدادات النظام ---
BAUD_RATE = 115200
MAX_RANGE = 150.0      # أقصى مدى للرادار (سم)
ALERT_DIST = 30.0      # مسافة التنبيه الحرجة (سم)
CAM_FOV = 66.0         # زاوية الرؤية الأفقية لكاميرا اللابتوب

current_angle = 90
current_distance = 400
scan_map = {a: 400 for a in range(181)}
point_life = {a: 0 for a in range(181)}
connected_port = "Searching..."
running = True

# قائمة لحفظ الأهداف المتعرف عليها لعرضها داخل الرادار
detected_targets = []

def find_arduino_port():
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        return None
    for p in ports:
        if "Arduino" in p.description or "CH340" in p.description or "USB" in p.description:
            return p.device
    return ports[-1].device

def serial_reader():
    global current_angle, current_distance, connected_port
    port = find_arduino_port()
    if not port:
        connected_port = "No Arduino Found"
        return

    try:
        ser = serial.Serial(port, BAUD_RATE, timeout=0.1)
        connected_port = port
        time.sleep(1.5)
        while running:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                parts = line.split(',')
                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                    ang = max(0, min(180, int(parts[0])))
                    dist = int(parts[1])
                    current_angle = ang
                    current_distance = dist
                    if 0 < dist <= MAX_RANGE:
                        scan_map[ang] = dist
                        point_life[ang] = 255
                    else:
                        scan_map[ang] = 400
                        point_life[ang] = 0
    except Exception:
        connected_port = f"Busy/Error: {port}"

threading.Thread(target=serial_reader, daemon=True).start()

model = YOLO("yolov8n.pt")
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
if not cap.isOpened():
    cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)

WINDOW_NAME = "Arduino Radar + Computer Vision"
cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_TOPMOST, 1)

def get_distance_at_angle(target_angle, tolerance=5):
    """جلب أقرب مسافة مقاسة من الألتراسونيك عند زاوية الجسم"""
    valid_dists = []
    for a in range(max(0, target_angle - tolerance), min(180, target_angle + tolerance + 1)):
        if scan_map[a] <= MAX_RANGE:
            valid_dists.append(scan_map[a])
    return min(valid_dists) if valid_dists else None

def draw_tactical_radar(canvas, cx, cy, radius, targets):
    """رسم الرادار التكتيكي مع طباعة أسماء الأجسام المكتشفة داخله"""
    # 1. أقواس المسافة
    for i in range(1, 5):
        r = int((radius / 4.0) * i)
        cv2.ellipse(canvas, (cx, cy), (r, r), 0, 180, 360, (160, 120, 0), 1)
        cv2.putText(canvas, f"{int((MAX_RANGE/4)*i)}cm", (cx + r - 28, cy - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (180, 160, 50), 1)

    # 2. خطوط الزوايا وحدود الكاميرا
    for a in range(30, 151, 30):
        rad = math.radians(a)
        x = int(cx + radius * math.cos(rad))
        y = int(cy - radius * math.sin(rad))
        cv2.line(canvas, (cx, cy), (x, y), (70, 60, 20), 1)

    for edge_a in [90 - CAM_FOV/2, 90 + CAM_FOV/2]:
        rad = math.radians(edge_a)
        x = int(cx + radius * math.cos(rad))
        y = int(cy - radius * math.sin(rad))
        cv2.line(canvas, (cx, cy), (x, y), (255, 200, 0), 2)

    # 3. نقاط المسح الخام للألتراسونيك
    for a in range(181):
        if point_life[a] > 0 and scan_map[a] <= MAX_RANGE:
            dist_px = (scan_map[a] / MAX_RANGE) * radius
            rad = math.radians(a)
            px = int(cx + dist_px * math.cos(rad))
            py = int(cy - dist_px * math.sin(rad))
            color = (60, 60, 255) if scan_map[a] <= ALERT_DIST else (50, 190, 255)
            cv2.circle(canvas, (px, py), 4, color, -1)
            point_life[a] = max(0, point_life[a] - 4)

    # 4. رسم الأجسام المتعرف عليها بالاسم داخل الرادار نفسه!
    for t in targets:
        # إذا كان الألتراسونيك قاس المسافة نستخدمها، وإلا نضع النقطة في منتصف مدى الكاميرا (75 سم)
        display_dist = t["dist"] if t["dist"] is not None else 75.0
        dist_px = (min(display_dist, MAX_RANGE) / MAX_RANGE) * radius
        rad = math.radians(t["angle"])
        tx = int(cx + dist_px * math.cos(rad))
        ty = int(cy - dist_px * math.sin(rad))

        is_danger = (t["dist"] is not None and t["dist"] <= ALERT_DIST)
        dot_color = (50, 50, 255) if is_danger else (0, 255, 130)

        # دائرة الهدف واسمه داخل الرادار
        cv2.circle(canvas, (tx, ty), 8, dot_color, -1)
        cv2.circle(canvas, (tx, ty), 12, dot_color, 1)

        radar_label = f"{t['name']} ({t['dist']}cm)" if t["dist"] else f"{t['name']}"
        cv2.rectangle(canvas, (tx - 10, ty - 28), (tx + len(radar_label)*8, ty - 12), (10, 15, 25), -1)
        cv2.putText(canvas, radar_label, (tx - 6, ty - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, dot_color, 1)

    # 5. شعاع السيرفو المتحرك
    beam_rad = math.radians(current_angle)
    bx = int(cx + radius * math.cos(beam_rad))
    by = int(cy - radius * math.sin(beam_rad))
    cv2.line(canvas, (cx, cy), (bx, by), (255, 255, 120), 2)
    cv2.circle(canvas, (cx, cy), 6, (255, 255, 0), -1)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    results = model(frame, verbose=False, conf=0.40)

    current_targets = []

    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cls_id = int(box.cls[0])
            label_name = model.names[cls_id].upper()
            conf = float(box.conf[0])

            # حساب زاوية الجسم بالنسبة للرادار
            center_x = (x1 + x2) / 2.0
            norm_x = (center_x / w) - 0.5
            obj_angle = max(0, min(180, int(90 - (norm_x * CAM_FOV))))

            # مطابقة الزاوية مع مسافة الألتراسونيك
            fused_dist = get_distance_at_angle(obj_angle)

            # حفظ الهدف لإرساله إلى شاشة الرادار
            current_targets.append({
                "name": label_name,
                "angle": obj_angle,
                "dist": fused_dist,
                "conf": conf,
                "area": (x2 - x1) * (y2 - y1)
            })

            # رسم المربع على الكاميرا
            if fused_dist is not None:
                box_color = (50, 50, 255) if fused_dist <= ALERT_DIST else (0, 230, 120)
                info_text = f"{label_name} | {fused_dist} cm"
            else:
                box_color = (255, 180, 0)
                info_text = f"{label_name} ({int(conf*100)}%)"

            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
            cv2.rectangle(frame, (x1, y1 - 26), (x1 + len(info_text)*10 + 10, y1), box_color, -1)
            cv2.putText(frame, info_text, (x1 + 5, y1 - 7),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (10, 10, 10), 2)

    # ترتيب الأهداف بحيث تظهر الأجسام الأصغر والأقرب (مثل الجوال أو علبة الماء) أولاً
    current_targets.sort(key=lambda item: item["area"])

    # إنشاء اللوحة المدمجة
    dashboard = np.zeros((h, w + 480, 3), dtype=np.uint8)
    dashboard[:] = (22, 13, 8)
    dashboard[0:h, 0:w] = frame

    # رسم الرادار في القسم الأيمن مع أسماء الأجسام داخله
    draw_tactical_radar(dashboard, w + 240, h - 45, 200, current_targets)

    # لوحة المعلومات العلوية داخل شاشة الرادار
    cv2.putText(dashboard, "TACTICAL RADAR // TARGET ID", (w + 20, 32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 225, 0), 2)
    cv2.putText(dashboard, f"Port: {connected_port} | Servo: {current_angle} deg", (w + 20, 58),
                cv2.FONT_HERSHEY_SIMPLEX, 0.48, (200, 200, 200), 1)

    # عرض قائمة الأهداف المرصودة نصياً في أعلى الرادار
    cv2.putText(dashboard, "DETECTED OBJECTS IN RADAR:", (w + 20, 88),
                cv2.FONT_HERSHEY_SIMPLEX, 0.48, (50, 220, 255), 1)

    if current_targets:
        for idx, t in enumerate(current_targets[:3]):  # عرض أهم 3 أجسام
            d_txt = f"{t['dist']} cm" if t["dist"] is not None else "Scanning..."
            row_txt = f"> {t['name']} | Angle: {t['angle']} deg | Dist: {d_txt}"
            row_col = (0, 255, 130) if t["dist"] is not None else (255, 200, 80)
            cv2.putText(dashboard, row_txt, (w + 20, 112 + idx * 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.48, row_col, 1)
    else:
        cv2.putText(dashboard, "> AREA CLEAR (No Objects)", (w + 20, 112),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (130, 150, 170), 1)

    cv2.imshow(WINDOW_NAME, dashboard)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        running = False
        break

cap.release()
cv2.destroyAllWindows()