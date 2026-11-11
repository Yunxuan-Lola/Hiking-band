# 运动状态识别

手表在徒步会话中以标称 25 Hz 读取 BMA423 三轴加速度，并使用 15 字节二进制 BLE 通知发送到树莓派。树莓派保存包含序号、手表运行时间、加速度、接收时间和断流标记的 CSV。每 50 个样本构成一个 2 秒窗口，窗口间隔 25 个样本；Python 提取 48 个特征并由 Random Forest 输出 `idle`、`walking`、`climbing` 或 `running`。

训练使用 SELFBack 公开腕部数据：`sitting/standing -> idle`、`walking -> walking`、`upstairs -> climbing`、`jogging -> running`；`downstairs` 不参与训练。训练传感器为 Axivity AX3，因此 [模型评估](model_evaluation.md) 的测试结果不能视为 T-Watch 的实测准确率。

训练、部署和离线回放命令见 [README](../README.md)。协议与任务设计见 [设计报告](design_report.md)。
