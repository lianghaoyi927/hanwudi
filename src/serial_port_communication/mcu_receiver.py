import serial
import struct

# ================= 配置区 =================
COM_PORT = 'COM9'  # 虚拟串口接收端
BAUDRATE = 115200
# =========================================

def main():
    try:
        ser = serial.Serial(COM_PORT, BAUDRATE, timeout=0.1)
        print(f"【虚拟电控】已连接 {COM_PORT}，等待接收数据...")

        buffer = b''

        while True:
            if ser.in_waiting > 0:
                buffer += ser.read(ser.in_waiting)

            # 动态处理变长帧
            while len(buffer) >= 5:
                # 1. 寻找帧头 0xAA
                if buffer[0] != 0xAA:
                    buffer = buffer[1:] # 不是帧头就丢弃，继续找
                    continue

                # 2. 至少要有 3 个字节才能读取长度字段
                if len(buffer) < 3:
                    break

                length = buffer[2]
                # 帧总长 = 帧头(1) + 功能码(1) + 长度(1) + 数据(length) + 校验(1) + 帧尾(1)
                frame_len = 1 + 1 + 1 + length + 1 + 1

                # 3. 如果数据不够一整帧，等待下一次接收
                if len(buffer) < frame_len:
                    break

                # 4. 截取完整一帧
                frame = buffer[:frame_len]
                buffer = buffer[frame_len:]

                # 5. 验证帧尾 0xBB
                if frame[-1] != 0xBB:
                    print("⚠️【虚拟电控】帧尾错误，丢弃此帧")
                    continue

                # 6. 验证校验和
                payload = frame[1:3+length]
                received_checksum = frame[3+length]
                calc_checksum = sum(payload) & 0xFF
                if received_checksum != calc_checksum:
                    print("⚠️【虚拟电控】校验和错误，丢弃此帧")
                    continue

                # 7. 解析功能码并处理
                func_code = payload[0]

                if func_code == 0x01:
                    # 解析视觉布尔值
                    vision_status = struct.unpack('<B', payload[2:])[0]
                    status_text = "检测到方块！" if vision_status == 1 else "未检测到方块"
                    print(f"✅【虚拟电控】收到视觉包: {status_text}")
                    
                elif func_code == 0x02:
                    # 回复心跳包
                    print("💓【虚拟电控】收到心跳包，回复 0x03")
                    reply_payload = struct.pack('<BBB', 0x03, 0x01, 0x00)
                    reply_checksum = sum(reply_payload) & 0xFF
                    reply_frame = struct.pack('<B', 0xAA) + reply_payload + struct.pack('<B', reply_checksum) + struct.pack('<B', 0xBB)
                    ser.write(reply_frame)

    except serial.SerialException as e:
        print(f"❌【错误】无法打开串口 {COM_PORT}。报错信息: {e}")
    except KeyboardInterrupt:
        print("\n【虚拟电控】接收停止。")
        if 'ser' in locals() and ser.is_open:
            ser.close()

if __name__ == "__main__":
    main()