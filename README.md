# Hiking Band: wearable activity recognition

TTGO T-Watch 2020 V3 collects wrist accelerometer data and sends it over BLE to a Raspberry Pi 3B+ running Linux. The Pi records the stream, runs a lightweight activity classifier, stores hiking sessions, and displays their summaries in a local web interface.

## Documentation

- [Design report](docs/design_report.md) and [PDF](docs/design_report.pdf): architecture, packet format, storage, failure handling, and verification status.
- [User manual](docs/user_manual.md) and [PDF](docs/user_manual.pdf): setup, watch workflow, offline checks, files, and troubleshooting.
- [Software requirements](docs/requirements.md): functional behavior and operating constraints.
- [Model evaluation](MODEL_EVALUATION.md): public-data metrics and limitations.

## Status and limitations

The motion pipeline uses a 25 Hz BMA423 accelerometer stream and a Random Forest trained with public wrist data. Training, recorded-data replay and protocol decoding can be tested without hardware. The watch firmware, BLE stability, actual sample timing, power use, and classifier performance on the BMA423 have **not** been verified on the target hardware. This is a research prototype, not a production or safety device.

The classifier has four output labels: `idle`, `walking`, `climbing`, and `running`. SELFBack `sitting` and `standing` map to idle, `walking` to walking, `upstairs` to climbing, and `jogging` to running. `downstairs` is excluded from training; hill ascent and true running are not specifically represented by those training labels. Do not interpret the output as validated hill or running detection. All movement recognition depends on wrist placement and behavior.

## Architecture

```
T-Watch BMA423 -> 25 Hz sampling task -> bounded queue -> BLE notifications
                                                         |
Pi: UUID discovery -> sequence check -> CSV recording -> 2 s window -> features -> model
                                          |                                |
                                  recordings/*.csv              session activity summary
```

Watch data uses a 15-byte little-endian packet (`<BHIhhhH`): version/type `0x11`, sequence (uint16), watch uptime in milliseconds (uint32), x/y/z in milligravity (int16), and cumulative queue/sensor drops (uint16). Each notification fits a default 20-byte ATT payload. A detected gap resets the partial inference window. The existing textual step-summary notification is handled separately. Each BLE connection with received motion data produces a CSV file under `RPi/recordings/`; it includes Pi receive time and a gap marker for later labeling and diagnostics. No offline retransmission or end-to-end delivery guarantee is implemented; sequence numbers help detect gaps.

## Training using public data

The implementation consumes the ZIP archive of [SELFBack's public wrist50 data](https://github.com/rgu-selfback/Datasets), collected with an Axivity AX3. Check the dataset's citation and usage terms before redistribution. The archive is not included in this repository. Training filters and resamples the 100 Hz recordings to 25 Hz, uses two-second windows with one-second hop, and splits subjects rather than overlapping windows between train and test. For practical runtime, the default uses up to 40 evenly spaced windows from each recording; `--max-windows 0` uses all.

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install numpy scipy scikit-learn==1.6.1
curl -L -o /tmp/selfback.zip https://github.com/rgu-selfback/Datasets/archive/refs/heads/master.zip
python RPi/train_public.py /tmp/selfback.zip \
  --model RPi/activity_model.pkl --report RPi/activity_report.json
```

The report records the label mapping, held-out subjects, per-class metrics and confusion matrix. See [MODEL_EVALUATION.md](MODEL_EVALUATION.md) for the current run and its limitations. Pickle artifacts must come from a trusted source, and the training and deployment scikit-learn versions must match. The generated model and raw recordings are ignored by Git. A public-data score measures held-out SELFBack participants, not performance on the watch.

For a quick end-to-end smoke check with a public sample (not a new evaluation score):

```sh
python RPi/export_public_sample.py /tmp/selfback.zip /tmp/walking.csv --subject 008 --label walking
python RPi/replay.py /tmp/walking.csv --model RPi/activity_model.pkl
```

## Raspberry Pi deployment

Use a supported 64-bit Raspberry Pi OS and Python 3.9 or newer; install the Bluetooth and build dependencies required by bluepy for your OS. Train the model in a compatible scikit-learn environment and copy the trusted artifact to `RPi/activity_model.pkl`. Run from the `RPi` directory:

```sh
python -m pip install -r requirements.txt
export HIKING_WATCH_MAC='AA:BB:CC:DD:EE:FF'
python receiver.py
# In another terminal:
python wserver.py
```

The web server binds to `127.0.0.1:5001` by default. `HIKING_BIND` can change the bind address. The existing login/database system is a local prototype with default credentials; do not expose it to untrusted networks without implementing proper authentication and secret management.
The development login initialized by the receiver is `user123` / `user123`. The web page shows saved sessions, not a live activity feed. `RPi/setup.sh` starts both services in the background after dependencies have been installed; foreground commands are easier to diagnose.

The receiver leaves activity as `unknown` when no compatible model exists. For offline replay of a recording:

```sh
python replay.py recordings/example.csv --model activity_model.pkl
```

## Watch firmware

Open `Watch/hikingassistant_RTOS/hikingassistant_RTOS.ino` with an ESP32 Arduino toolchain and the LilyGO TTGO T-Watch library configured for T-Watch 2020 V3. The main application code is in `hikingassistant.cpp`. The firmware uses the library's BMA423 driver and existing FreeRTOS tasks. It configures ±2 g at 25 Hz and converts 1024 LSB/g to mg; verify the library version, device variant, axis orientation, and measured static gravity before deployment. Strong impacts and running may saturate the ±2 g range; validate whether a wider range and retraining are needed. The old nested `hikingassistant_with_activity_recognition` sketch is an earlier draft and is not the canonical firmware.

## Validation

```sh
python -m unittest discover -s tests -v
```

The watch sketch was compiled with Arduino ESP32 core 2.0.17 and TTGO TWatch Library 1.4.2. Hardware validation still needed: verify sensor scaling and sampling jitter, notification subscription and reconnects, dropped samples, long-run storage and power use; then collect labeled T-Watch data from multiple sessions and users to measure real-device generalization.
