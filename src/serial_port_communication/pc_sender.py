import serial
import struct
import time
import random

# ================= 配置区 =================
# 提示：上传代码库前，请确保使用者知道要把 COM7 改成他们自己电脑的端口号
COM_PORT = 'COM7' 
BAUDRATE = 115200
# =========================================

def main():
    try:
        # 打开串口
        ser = serial.Serial(COM_PORT, BAUDRATE, timeout=0.1)
        print(f"【上位机】已连接 {COM_PORT}，波特率 {BAUDRATE}，开始发送数据...")

        # 记录心跳和接收时间戳
        last_heartbeat_time = time.time()
        last_receive_time = time.time()

        while True:
            # 1. 模拟视觉状态 (0: 未检测到, 1: 检测到)
            vision_status = random.choice([0, 1])
            
            # 2. 构造数据帧
            func_code = 0x01  # 功能码：视觉状态
            data_content = struct.pack('<B', vision_status)
            length = len(data_content)
            
            # 拼装载荷：功能码 + 长度 + 数据
            payload = struct.pack('<BB', func_code, length) + data_content
            # 计算校验和
            checksum = sum(payload) & 0xFF
            # 完整帧：帧头(0xAA) + 载荷 + 校验 + 帧尾(0xBB)
            frame = struct.pack('<B', 0xAA) + payload + struct.pack('<B', checksum) + struct.pack('<B', 0xBB)
            
            ser.write(frame)
            status_text = "检测到方块" if vision_status == 1 else "未检测到方块"
            print(f"【上位机】发送视觉包: {status_text} | 数据: {frame.hex()}")

            # 3. 发送心跳包 (每1秒一次)
            if time.time() - last_heartbeat_time > 1.0:
                # 心跳包格式：AA 02 01 00 03 BB (统一6字节)
                hb_payload = struct.pack('<BBB', 0x02, 0x01, 0x00)
                hb_checksum = sum(hb_payload) & 0xFF
                hb_frame = struct.pack('<B', 0xAA) + hb_payload + struct.pack('<B', hb_checksum) + struct.pack('<B', 0xBB)
                
                ser.write(hb_frame)
                print(f"【上位机】发送心跳包 0x02")
                last_heartbeat_time = time.time()

            # 4. 接收电控回复，判断超时
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                # print(f"【调试】收到电控发来的数据: {data.hex()}") # 需要调试时取消注释
                last_receive_time = time.time()
                
            # 如果超过 3 秒没收到回复，触发警告
            if time.time() - last_receive_time > 3.0:
                print("🚨【警告】超过 3 秒未收到电控回复！通信可能断开！🚨")
                last_receive_time = time.time() # 重置，避免刷屏
                
            time.sleep(0.5) # 循环间隔

    except serial.SerialException as e:
        print(f"❌【错误】无法打开串口 {COM_PORT}，请检查端口是否被占用或不存在。报错信息: {e}")
    except KeyboardInterrupt:
        print("\n【上位机】发送停止。")
        if 'ser' in locals() and ser.is_open:
            ser.close()

if __name__ == "__main__":
    main()