# Project documents

The documents in this directory describe the deployable Hiking Assistant code and its measured limits.

| Document | Purpose |
| --- | --- |
| [Requirements](requirements.md) | Functions, constraints and verification traceability |
| [Design report](design_report.md) · [PDF](design_report.pdf) | Firmware, BLE protocol, Pi data flow, storage and failure handling |
| [User manual](user_manual.md) · [PDF](user_manual.pdf) | Setup, session operation, offline checks and troubleshooting |
| [Model evaluation](model_evaluation.md) | Public wrist-data results and interpretation limits |
| [Chinese overview](overview_zh.md) | Brief project introduction |
| [Chinese code guide](code_guide_zh.md) | Source module map |
| [Chinese activity note](activity_recognition_zh.md) | Classifier inputs, labels and training data |
| [Chinese project summary](project_summary_zh.md) | Concise system feature summary |

`build_pdfs.py` regenerates the design report and user manual PDFs from their Markdown sources. It requires `reportlab` and a standard Arial or DejaVu font; Helvetica is used as a fallback.
