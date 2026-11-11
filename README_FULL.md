# Hiking Assistant 项目说明

Hiking Assistant 使用 TTGO T-Watch 2020 V3 内置 BMA423 采集腕部三轴加速度和步数，通过 BLE 将运动数据发送到 Raspberry Pi 3B+。树莓派保存原始数据流，运行轻量运动状态分类器，并在本地网页展示徒步会话摘要。

系统输出 `idle`、`walking`、`climbing` 和 `running` 四类。模型基于公开的 SELFBack 腕部数据训练，其中上楼数据对应 `climbing`，慢跑数据对应 `running`。该数据来自 Axivity AX3，尚需用 T-Watch 实测数据验证跨设备表现。

完整的安装与使用方法见 [README](README.md) 和 [用户手册](docs/user_manual.md)；架构、BLE 协议与数据处理见 [设计报告](docs/design_report.md)；需求与限制见 [软件需求](docs/requirements.md)。
