import cv2
import numpy as np
import serial
import time

#基本思路：截取一定面积的摄像头，计算面积，当面积达到阈值时，方块就基本在中间了
# 初始化串口和摄像头
ser = serial.Serial('/dev/ttyS0', 115200)
cap = cv2.VideoCapture(0)

# 2. 定义状态和参数
debug_mode = True
TARGET_AREA = 3000  # 这个数字调试时用
current_status = 0x00

while True:
    ret, frame = cap.read()
    if not ret: break

    # 截取中间 ROI（假设取中间的 300x300 区域）
    # 后面再调试
    roi = frame[90:390, 170:470]

    # 转 HSV
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

    # 形态学去噪（开闭运算）
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # 找轮廓
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    current_status = 0x00  # 默认没找到

    if len(contours) > 0:
        # 找最大的轮廓
        c = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(c)
        x, y, w, h = cv2.boundingRect(c)

        # 核心过滤：面积够大，且宽高比像正方形
        if area > 500 and 0.7 < (w / h) < 1.3:

            if debug_mode:
                # 调试模式：用面积判断距离
                if area < TARGET_AREA * 0.8:
                    current_status = 0x01  # 远
                elif area > TARGET_AREA * 1.2:
                    current_status = 0x02  # 近
                else:
                    current_status = 0x03
            else:
                # 比赛模式：面积达到了就直接给对齐信号
                if area >= TARGET_AREA * 0.9:
                    current_status = 0x01

            # 画个绿框和文字方便操作手看
            cv2.rectangle(roi, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(roi, f"Area:{int(area)}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    # 发送串口数据
    checksum = 0xAA ^ current_status
    ser.write(bytes([0xAA, current_status, checksum, 0x55]))

    # 显示画面
    cv2.imshow("ROI", roi)
    cv2.imshow("Mask", mask)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
ser.close()
cv2.destroyAllWindows()