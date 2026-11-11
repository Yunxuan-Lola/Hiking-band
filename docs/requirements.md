# Hiking Assistant - software requirements

This document defines the implemented behavior and operating constraints of the Hiking Assistant system. Hardware-dependent behavior still requires measurement on the target devices.

## Functional requirements

- **R1 - motion sampling:** During a watch session, sample the onboard BMA423's three acceleration axes at a nominal 25 Hz and represent each axis in milligravity. Outside an active session, stop the stream.
- **R2 - BLE transport:** Send each sample as a 15-byte versioned notification containing sequence, watch uptime, X/Y/Z, and cumulative producer drops. Keep the existing step-summary upload and acknowledgement path.
- **R3 - resilient receiver:** Decode and reject malformed binary packets, detect sequence/time/drop discontinuities, discard partial inference windows on a gap, and retry the BLE connection after a disconnect.
- **R4 - raw data retention:** Save received motion samples to per-connection CSV files on the Pi; separate the recording worker from inference and bound both queues.
- **R5 - activity inference:** When a compatible trusted model is present, classify 2-second windows every second into `idle`, `walking`, `climbing`, or `running`. When absent, continue other functions and report activity `unknown`.
- **R6 - summary and display:** Store dominant activity and prediction-window share with steps, distance, and estimated calories in SQLite. Show saved sessions newest first after local login.
- **R7 - reproducible training:** Support retraining from the public SELFBack wrist50 archive with a subject-disjoint evaluation, a recorded class mapping, model metadata, and a report.

## Nonfunctional targets and limits

The nominal motion period is 40 ms; actual jitter and BLE throughput have not been measured on the target devices. A single notification fits the default 20-byte ATT payload. Watch and Pi queues are bounded to avoid unbounded memory growth, but overflow causes loss. The receiver detects gaps; it does not recover samples. The web service is localhost-only by default and has prototype authentication. No production availability, power, security, medical, or motion-accuracy target is claimed.

## Traceability

| Requirement | Implementation | Verification available |
| --- | --- | --- |
| R1-R2 | `Watch/hikingassistant_RTOS/hikingassistant.cpp` | Compile check; hardware measurement pending |
| R3-R4 | `RPi/bt.py`, `RPi/stream_protocol.py` | Packet, gap, and CSV worker tests |
| R5 | `RPi/features.py`, `RPi/activity_rec.py` | Window/feature tests and offline replay |
| R6 | `RPi/db.py`, `RPi/wserver.py`, `RPi/templates/home.html` | Database tests; browser/hardware workflow pending |
| R7 | `RPi/train_public.py`, `docs/model_evaluation.md` | Subject-disjoint public-data evaluation |

The design report and user manual are `docs/design_report.md` and `docs/user_manual.md`.
