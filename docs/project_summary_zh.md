# Hiking Assistant 项目概览

项目包含手表端运动采样与计步、BLE 数据传输、树莓派异步数据记录、运动状态推理、会话摘要持久化和本地网页展示。原始运动数据存储为 CSV，会话摘要存储在 SQLite；记录文件保留接收时间与断流信息，便于回放、标注和故障分析。

项目说明与操作命令见 [README](../README.md) 和 [用户手册](user_manual.md)。系统架构及设计取舍见 [设计报告](design_report.md)，功能需求见 [软件需求](requirements.md)，公开数据评估见 [模型评估](model_evaluation.md)。
