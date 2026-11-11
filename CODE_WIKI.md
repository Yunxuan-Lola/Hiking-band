# Hiking Assistant 代码导览

## 手表端

`Watch/hikingassistant_RTOS/hikingassistant_RTOS.ino` 是 Arduino 工程入口，`hikingassistant.cpp` 实现 FreeRTOS 任务、BMA423 采样、硬件计步和 BLE 通知。`inc/events.h`、`src/events.cpp` 管理应用事件队列；`inc/ui.h`、`src/ui.cpp` 绘制手表界面。

## 树莓派端

`RPi/receiver.py` 启动 BLE 接收和会话处理；`bt.py` 负责连接、二进制运动帧接收、异步 CSV 写入及断流检测；`stream_protocol.py` 解码 15 字节 BLE 数据帧。`features.py` 提取窗口特征，`activity_rec.py` 运行模型推理，`train_public.py` 从 SELFBack 腕部数据训练模型，`replay.py` 离线回放 CSV。`db.py`、`hike.py` 和 `wserver.py` 负责会话持久化与本地网页展示。

协议字段、数据格式、任务关系、失败处理和验证边界见 [设计报告](docs/design_report.md)。运行命令见 [README](README.md) 和 [用户手册](docs/user_manual.md)。
