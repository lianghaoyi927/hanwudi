# CRTC机器人训练赛 
# 硬件与EDA学习记录（Day 1）
## 🎯 今日目标
熟悉嘉立创EDA基础操作，理解电路回路，完成9V转5V稳压+按键控制LED原理图。
![电路元件图](images/eda画图学习.png)
## 📚 今日学了什么
- **元件**：电容0.1µF=100nF；电阻直接放通用件改Value；LED长脚为正需限流；按键用四脚直插，无极性。
- **EDA**：快捷键`Shift+F`搜元件、`W`画线、`V`/`G`放电源地；画完必须跑ERC查悬空。
- **逻辑**：电流需电位差和闭合回路；开关接GND侧（低边开关）；滤波电容必须并联在电源与地之间。
## 🛠️ 实战电路
9V电池 -> L7805转5V -> LED正极 -> LED负极 -> 300Ω电阻 -> 按键 -> GND。
C1(10µF) 与 C2(100nF) 并联在电源和GND之间滤波。


# 串口通信学习记录（Day 2）

> **目标**：搭建Python串口环境，理解收发原理，跑通虚拟回环测试。

## 📚 今日学了什么
- **环境搭建**：安装VS Code，Python 3.13，`pyserial`库（`pip install pyserial`）。
- **核心原理**：串口通信是比特流（0和1）转化为物理电压（0V/3.3V）的传输过程。接线必须**TX接RX，RX接TX，GND共地**。
- **调试技巧**：学会使用 `ser.in_waiting` 查看缓冲区，`ser.read()` 读取数据，以及 `data.hex().upper()` 将字节流转为可视十六进制。

## 🛠️ 实操记录
1. **虚拟回环**：在没有硬件的情况下，开启本地回环测试。
2. **发送测试**：发送十六进制指令 `AA55016400C8005A`。
3. **接收验证**：`in_waiting` 返回8，读取并成功打印出原指令，证明收发逻辑跑通。
![串口](images/串口1.png)
## ⚠️ 踩坑与经验
1. **虚拟串口兼容性**：`com0com`下载困难，且`loop://`在Windows下不能直接用`serial.Serial()`，必须用`serial_for_url()`。

## 🚀 下一步
- [ ] 修改 `test_loop.py` 脚本文件，完成一键自动收发。
- [ ] 尝试别的路径下载com0com，用serial本地回环太复杂，后面和电控沟通代码会很麻烦。
- [ ] 与电控同学确定波特率和数据帧还有常用指令，准备与电控队友进行真实串口联调。




# 9.27串口学习内容
# Python 串口通信测试代码（虚拟串口 COM8 ↔ COM9）

## 环境说明
- 虚拟串口软件：VSPD（Virtual Serial Port Driver）
- 虚拟端口对：COM8（发送端）、COM9（接收端）
- 波特率：9600
- Python 库：pyserial
- 运行环境：PyCharm（或任意 Python 环境）

---

## 一、发送端代码（脚本1.py）

```python
import serial
import time

# 打开 COM8 发送数据
try:
    ser = serial.Serial('COM8', 9600, timeout=1)
    print("COM8 已打开，开始发送数据...")

    while True:
        ser.write(b'Hello from COM8!\n')
        print("已发送: Hello from COM8!")
        time.sleep(1)  # 每秒发一次

except serial.SerialException as e:
    print(f"打开 COM8 失败: {e}")
except KeyboardInterrupt:
    print("\n发送停止。")
    if 'ser' in locals() and ser.is_open:
        ser.close()
```
## 二、接收端代码（脚本2.py）

```python
import serial

# 打开 COM9 接收数据
try:
    ser = serial.Serial('COM9', 9600, timeout=1)
    print("COM9 已打开，等待接收数据...")

    while True:
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting)
            print(f"COM9 收到: {data}")

except serial.SerialException as e:
    print(f"打开 COM9 失败: {e}")
except KeyboardInterrupt:
    print("\n接收停止。")
    if 'ser' in locals() and ser.is_open:
        ser.close()
```
## 三、注意事项
- 打开串口的代码必须放在**try 块**中，捕获 SerialException，否则程序容易闪退。
- 虚拟串口的端口号在不同电脑上可能不同，使用前务必去“设备管理器 → 端口 (COM 和 LPT)”**确认实际端口号**，并**同步修改代码**。




# 10.2 Python 串口通信学习记录（阶段一：纯软件逻辑测试）

## 学习日期

2026年10月2日

## 阶段目标

在没有物理硬件的情况下，利用虚拟串口（COM8 ↔ COM9）跑通**数据帧打包、动态解析、容错过滤、心跳保活**的完整通信闭环。

## 环境信息

- 编程语言：Python 3.13
- 开发工具：PyCharm
- 核心库：pyserial（串口通信）、struct（二进制打包）、time（时间控制）
- 通信端口：发送端 COM8，接收端 COM9（VSPD虚拟串口）

## 协议设计（核心成果）

今天经历多次调试，最终确定了一套**支持变长帧的标准通信协议**：

```
[帧头 0xAA] [功能码 1字节] [数据长度 1字节] [数据内容 N字节] [校验和 1字节] [帧尾 0xBB]
```

**已实现的功能码：**

- `0x01`：视觉坐标传输（数据内容为 X坐标 2字节 + Y坐标 2字节）
- `0x02`：心跳包（数据长度为 0，无数据内容）
- `0x03`：心跳回复（由接收端模拟电控回复）

**校验规则**：功能码 + 数据长度 + 数据内容，所有字节相加取低8位。

## 核心代码实现

### 1. 发送端代码（pc_sender.py）

```python
import serial
import struct
import time
import random

try:
    ser = serial.Serial('COM8', 9600, timeout=0.1)
    print("【上位机】已连接 COM8，开始发送数据...")

    target_x = 320
    target_y = 240
    count = 0
    
    last_heartbeat_time = time.time()
    last_receive_time = time.time()

    while True:
        count += 1
        
        # --- 1. 发送视觉坐标 ---
        func_code = 0x01
        data_content = struct.pack('<HH', target_x, target_y)
        length = len(data_content)
        payload = struct.pack('<BB', func_code, length) + data_content
        checksum = sum(payload) & 0xFF
        frame = struct.pack('<B', 0xAA) + payload + struct.pack('<B', checksum) + struct.pack('<B', 0xBB)
        
        ser.write(frame)
        print(f"【上位机】发送坐标: x={target_x}, y={target_y}")
        target_x = random.randint(280, 400)

        # --- 2. 发送心跳包（每1秒一次） ---
        if time.time() - last_heartbeat_time > 1.0:
            hb_payload = struct.pack('<BB', 0x02, 0x00)
            hb_checksum = sum(hb_payload) & 0xFF
            hb_frame = struct.pack('<B', 0xAA) + hb_payload + struct.pack('<B', hb_checksum) + struct.pack('<B', 0xBB)
            ser.write(hb_frame)
            print("【上位机】发送心跳包 0x02")
            last_heartbeat_time = time.time()

        # --- 3. 接收电控回复，判断超时 ---
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting)
            last_receive_time = time.time()
            
        if time.time() - last_receive_time > 3.0:
            print("【警告】超过 3 秒未收到电控回复！通信可能断开！")
            last_receive_time = time.time()
            
        time.sleep(0.5)

except serial.SerialException as e:
    print(f"【错误】无法打开串口: {e}")
except KeyboardInterrupt:
    print("\n【上位机】发送停止。")
    if 'ser' in locals() and ser.is_open:
        ser.close()
```

### 2. 接收端代码（mcu_receiver.py）

```python
import serial
import struct

try:
    ser = serial.Serial('COM9', 9600, timeout=0.1)
    print("【电控模拟】已连接 COM9，等待接收数据...")

    buffer = b''

    while True:
        if ser.in_waiting > 0:
            buffer += ser.read(ser.in_waiting)

        # 动态处理变长帧
        while len(buffer) >= 5:
            # 寻找帧头
            if buffer[0] != 0xAA:
                buffer = buffer[1:]
                continue

            if len(buffer) < 3:
                break

            length = buffer[2]
            frame_len = 1 + 1 + 1 + length + 1 + 1

            if len(buffer) < frame_len:
                break

            frame = buffer[:frame_len]
            buffer = buffer[frame_len:]

            # 验证帧尾
            if frame[-1] != 0xBB:
                print("【电控模拟】帧尾错误，丢弃此帧")
                continue

            payload = frame[1:3+length]
            received_checksum = frame[3+length]

            # 验证校验和
            calc_checksum = sum(payload) & 0xFF
            if received_checksum != calc_checksum:
                print("【电控模拟】校验和错误，丢弃此帧")
                continue

            func_code = payload[0]

            if func_code == 0x01:
                x, y = struct.unpack('<HH', payload[2:])
                print(f"【电控模拟】解析成功！收到视觉坐标: x={x}, y={y}")
            elif func_code == 0x02:
                print("【电控模拟】收到心跳包！回复 0x03")
                reply_payload = struct.pack('<BB', 0x03, 0x00)
                reply_checksum = sum(reply_payload) & 0xFF
                reply_frame = struct.pack('<B', 0xAA) + reply_payload + struct.pack('<B', reply_checksum) + struct.pack('<B', 0xBB)
                ser.write(reply_frame)

except serial.SerialException as e:
    print(f"【错误】无法打开串口: {e}")
except KeyboardInterrupt:
    print("\n【电控模拟】接收停止。")
    if 'ser' in locals() and ser.is_open:
        ser.close()
```

## 调试过程中解决的三个核心技术难题

1. **粘包与半包问题**：通过 buffer 缓冲区 + while 循环，实现“凑够一帧才解析”。接收端绝对不会因为一次性收到多帧或者半帧数据而崩溃。
2. **变长帧的动态解析（重要）**：早期代码写死了 `len(buffer) >= 8`，导致长度为 5 字节的心跳包无法被解析，引发“超过3秒未回复”的假报警。后来改为读取 `buffer[2]` 作为长度字段，动态计算 `frame_len`，完美解决。
3. **容错与抗干扰**：发送端故意注入 `11223344` 乱码，接收端通过帧头 `0xAA` 和帧尾 `0xBB` 的验证，能够自动丢弃无效数据，不执行错误指令。

## 下一步计划（硬件联调准备）

1. **备份当前成功代码**：将 `pc_sender.py` 和 `mcu_receiver.py` 复制到“阶段一_成功版备份”文件夹。
2. **硬件到货测试**：USB 转 TTL 模块和 HC-05 蓝牙模块到货后，先进行物理回环测试（TX与RX短接），再进行有线联调，最后上蓝牙。
3. **联调前清理工作**：在和电控同学对接真实 STM32 之前，务必删除或注释掉发送端中故意发送乱码 `11223344` 的测试代码，以免占用蓝牙带宽、干扰真实通信。

---

注：本文档为阶段一（虚拟串口软件逻辑）学习记录，后续硬件联调将基于此版本代码进行移植。