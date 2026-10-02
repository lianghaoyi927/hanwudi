# 串口通信协议设计文档

**队伍：** 焊武帝  
**机器人数量：** 2台  
**文档版本：** V1.0  
**日期：** 2026年10月  
**负责人：** 梁皓贻
**参与讨论：** 梁皓贻 刘常兴

---

## 1. 串口通信协议总体设计

### 1.1 功能描述

串口通信协议负责打通**上位机（视觉系统/Python）**与**下位机（STM32电控系统）**之间的数据链路，确保视觉识别结果、心跳保活、电控回复等数据能够稳定传输。本系统的设计目标是：**在没有物理硬件的阶段，先用虚拟串口跑通完整的通信闭环，为后续硬件联调做好准备。**

### 1.2 开发历程：为什么协议要尽早定稿？

根据9月30日组会要求，串口组需制定串口协议，与电控组完成对接，确保视觉、电控等模块之间通信稳定。协议需明确数据格式、波特率、校验方式、收发逻辑等，提前预留调试接口，方便后期联调。

**为什么协议要尽早定稿？**

- 视觉组需要按照协议格式输出数据。
- 电控组需要按照协议格式解析数据。
- 如果协议定得太晚，两边无法并行开发，会拖慢整体进度。
- 提前定稿后，视觉组可以在没有硬件的情况下，先用虚拟串口测试软件逻辑。

### 1.3 开发环境

| 项目 | 内容 |
|---|---|
| 编程语言 | Python 3.13 |
| 开发工具 | PyCharm |
| 核心库 | pyserial（串口通信）、struct（二进制打包）、time（时间控制） |
| 通信端口 | 发送端 COM8，接收端 COM9（VSPD虚拟串口） |
| 测试阶段 | 阶段一：纯软件逻辑测试（无物理硬件） |

---

## 2. 通信协议帧格式设计

### 2.1 功能描述

本板块定义了一套**支持变长帧的标准通信协议**，用于上位机与下位机之间的数据传输。协议需要同时支持多种数据类型（视觉坐标、心跳包、心跳回复），并能正确解析变长数据。

### 2.2 开发历程：为什么选择变长帧而不是固定帧？

**早期方案的缺陷：**

- 最初设计时，为了简化解析逻辑，考虑过使用固定长度帧。但视觉坐标数据需要传输X、Y两个坐标（各2字节），而心跳包不需要传输任何数据。如果用固定帧，心跳包也必须凑够相同的字节数，造成带宽浪费。
- 如果用固定帧，接收端必须写死帧长度（如 `len(buffer) >= 8`），一旦后续增加新的功能码（如传输角度、距离），帧长度会变化，代码需要重新修改，扩展性差。

**变长帧方案的优势：**

- 帧内自带“数据长度”字段，接收端可以根据该字段动态计算帧长。
- 心跳包数据长度为0，只占5个字节；视觉坐标帧数据长度为4，占9个字节。各取所需，不浪费带宽。
- 后续增加新功能码时，只需扩展功能码和数据内容，协议格式不变，接收端代码无需大改。

### 2.3 协议帧格式

```text
[帧头 0xAA] [功能码 1字节] [数据长度 1字节] [数据内容 N字节] [校验和 1字节] [帧尾 0xBB]
```

**字段说明：**

| 字段 | 长度 | 说明 |
|---|---|---|
| 帧头 | 1字节 | 固定为 0xAA，用于标识一帧数据的开始 |
| 功能码 | 1字节 | 标识数据类型（0x01视觉坐标、0x02心跳、0x03心跳回复） |
| 数据长度 | 1字节 | 数据内容的字节数（N） |
| 数据内容 | N字节 | 具体数据（如X坐标2字节+Y坐标2字节） |
| 校验和 | 1字节 | 功能码+数据长度+数据内容，所有字节相加取低8位 |
| 帧尾 | 1字节 | 固定为 0xBB，用于标识一帧数据的结束 |

### 2.4 已实现的功能码

| 功能码 | 名称 | 数据长度 | 数据内容 | 说明 |
|---|---|---|---|---|
| 0x01 | 视觉坐标传输 | 4字节 | X坐标2字节 + Y坐标2字节 | 上位机发送给下位机 |
| 0x02 | 心跳包 | 0字节 | 无 | 上位机定时发送，保活 |
| 0x03 | 心跳回复 | 0字节 | 无 | 下位机收到心跳后回复 |

### 2.5 校验规则

校验和 = 功能码 + 数据长度 + 数据内容，所有字节相加取低8位。

**为什么选择校验和而不是CRC？**

- 校验和计算简单，Python和C语言都能轻松实现，不需要额外依赖库。
- 本协议的传输数据量小（单帧最多9字节），校验和足以检测出常见的传输错误。
- CRC-16校验虽然更可靠，但计算复杂度高，对新生赛来说没有必要。

---

## 3. 发送端软件设计

### 3.1 功能描述

发送端（pc_sender.py）运行在上位机，负责**打包视觉坐标数据、定时发送心跳包、监测通信超时**。

### 3.2 开发历程：为什么需要心跳包？

**问题**：上位机需要知道下位机是否在线。如果下位机突然断电或程序崩溃，上位机应该能感知到通信断开，而不是一直盲目发送数据。

**解决方案**：设计心跳机制。

- 上位机每1秒发送一次心跳包（功能码0x02）。
- 下位机收到心跳包后，回复心跳回复（功能码0x03）。
- 上位机如果超过3秒没有收到任何回复，就判断通信断开，打印警告。

**为什么心跳间隔是1秒、超时阈值是3秒？**

- 1秒间隔足够短，能及时发现通信异常，又不会占用太多带宽。
- 3秒超时阈值给了下位机足够的处理时间，避免因为短暂延迟导致误报。

### 3.3 核心代码实现

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

---

## 4. 接收端软件设计

### 4.1 功能描述

接收端（mcu_receiver.py）模拟下位机（STM32电控），负责**接收上位机发送的数据帧、动态解析变长帧、校验帧头帧尾和校验和、回复心跳**。

### 4.2 开发历程：如何解决粘包、半包和变长帧问题？

**问题一：粘包与半包**

串口通信中，接收端一次性收到的数据可能是：

- 完整的一帧；
- 多帧粘在一起（粘包）；
- 半帧（半包）。

如果直接按固定长度读取，一旦粘包或半包，解析就会出错。

**解决方案**：使用 `buffer` 缓冲区 + `while` 循环，实现“凑够一帧才解析”。

- 把收到的所有数据追加到 `buffer` 中。
- 每次循环时，先寻找帧头 `0xAA`，如果不是帧头就丢弃前面的字节。
- 然后读取 `buffer[2]` 作为数据长度字段，动态计算 `frame_len`。
- 如果 `buffer` 长度不够 `frame_len`，就退出循环，等待下一批数据。
- 如果够，就截取一帧，处理，然后把这一帧从 `buffer` 中删除。

**问题二：变长帧的动态解析（重要）**

早期代码写死了 `len(buffer) >= 8`，导致长度为5字节的心跳包无法被解析，引发“超过3秒未回复”的假报警。

**解决方案**：改为读取 `buffer[2]` 作为长度字段，动态计算 `frame_len = 1 + 1 + 1 + length + 1 + 1`。心跳包长度为5，视觉坐标帧长度为9，都能正确解析。

**问题三：容错与抗干扰**

发送端故意注入 `11223344` 乱码，接收端通过帧头 `0xAA` 和帧尾 `0xBB` 的验证，能够自动丢弃无效数据，不执行错误指令。

**解决方案**：在解析每一帧时，先验证帧尾是否为 `0xBB`，再验证校验和是否正确。任何一步失败，就丢弃此帧，继续处理下一个字节。

### 4.3 核心代码实现

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

---

## 5. 调试过程中解决的核心技术难题

### 5.1 难题一：粘包与半包

| 项目 | 说明 |
|---|---|
| 问题描述 | 串口通信中，接收端一次性收到的数据可能是完整帧、多帧粘连或半帧 |
| 解决方案 | 使用 `buffer` 缓冲区 + `while` 循环，凑够一帧才解析 |
| 效果 | 接收端不会因为粘包或半包而崩溃 |

### 5.2 难题二：变长帧的动态解析

| 项目 | 说明 |
|---|---|
| 问题描述 | 早期代码写死 `len(buffer) >= 8`，长度为5的心跳包无法解析，引发假报警 |
| 解决方案 | 读取 `buffer[2]` 作为长度字段，动态计算 `frame_len` |
| 效果 | 心跳包（5字节）和视觉坐标帧（9字节）都能正确解析 |

### 5.3 难题三：容错与抗干扰

| 项目 | 说明 |
|---|---|
| 问题描述 | 发送端故意注入 `11223344` 乱码，测试接收端能否过滤无效数据 |
| 解决方案 | 通过帧头 `0xAA` 和帧尾 `0xBB` 的验证，自动丢弃无效数据 |
| 效果 | 接收端不会执行错误指令，通信稳定性得到验证 |

---

## 6. 下一步计划（硬件联调准备）

### 6.1 功能描述

阶段一（虚拟串口软件逻辑）已经跑通，下一步需要为真实硬件联调做准备。

### 6.2 开发历程：为什么必须先做物理回环测试？

在虚拟串口测试中，收发双方都在同一台电脑上，通信环境理想。但真实硬件联调会面临：

- USB转TTL模块的驱动兼容性问题；
- 硬件串口的波特率误差；
- 蓝牙模块的配对和延迟问题。

如果直接上真实硬件联调，一旦出问题，很难判断是软件逻辑错误还是硬件连接错误。所以必须先做物理回环测试（TX与RX短接），验证硬件本身能正常收发，再进行有线联调，最后上蓝牙。

### 6.3 下一步计划清单

| 序号 | 任务 | 说明 |
|---|---|---|
| 1 | 备份当前成功代码 | 将 `pc_sender.py` 和 `mcu_receiver.py` 复制到“阶段一_成功版备份”文件夹 |
| 2 | 硬件到货测试 | USB转TTL模块和HC-05蓝牙模块到货后，先做物理回环测试（TX与RX短接） |
| 3 | 有线联调 | 用USB转TTL模块连接PC和STM32，测试真实通信 |
| 4 | 蓝牙联调 | 在有线联调成功后，切换到HC-05蓝牙模块 |
| 5 | 联调前清理工作 | 删除或注释掉发送端中故意发送乱码 `11223344` 的测试代码，以免占用蓝牙带宽、干扰真实通信 |

---

**文档结束**

**记录人：** 梁皓贻
**审核：** 梁皓贻  
**日期：** 2026年10月  
**版本：** V1.0