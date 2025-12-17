#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

#include "inc/config.h"
#include "inc/ui.h"
#include "inc/events.h"

TTGOClass *watch;
TFT_eSPI *tft;
BMA *sensor;

int16_t x, y;
char buffer[50];
AppContext app = {
APP_IDLE,   // state
    0,          // currentSteps
    0,          // previousSteps
    0.0f        // previousDistance
};

// BLE Setup
BLEServer *pServer = nullptr;
BLECharacteristic *pTxCharacteristic = nullptr;
BLESecurity *pSecurity = new BLESecurity();
bool deviceConnected = false;
bool oldDeviceConnected = false;

volatile bool irq = false;

#define SERVICE_UUID "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
#define CHARACTERISTIC_UUID_RX "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
#define CHARACTERISTIC_UUID_TX "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) { deviceConnected = true; }
    void onDisconnect(BLEServer* pServer) { deviceConnected = false; }
};

class MyCallbacks: public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pCharacteristic) {
        std::string rxValue = pCharacteristic->getValue();
        Serial.print("Received Value: ");
        Serial.println(rxValue.c_str());
        if (rxValue == "r") {
            enqueueEvent(EV_UPLOAD_ACK);
        }
    }
};

void IRAM_ATTR stepInterruptHandler() {
    irq = true;
}

bool touchInRect(int16_t tx, int16_t ty, int x0, int y0, int x1, int y1) {
    return (tx > x0 && tx < x1 && ty > y0 && ty < y1);
}

void pollTouch() {
    if (!watch->getTouch(x, y)) return;

    switch (app.state) {
    case APP_IDLE:
    case APP_COUNTING:
        if (touchInRect(x, y, 50, 180, 170, 220)) {
            enqueueEvent(app.state == APP_IDLE ? EV_START : EV_STOP);
        }
        break;
    case APP_SESSION_FINISHED:
        if (touchInRect(x, y, 20, 180, 120, 220)) {
            enqueueEvent(EV_UPLOAD_SELECTED);
        } else if (touchInRect(x, y, 120, 180, 220, 220)) {
            enqueueEvent(EV_DISCARD_SESSION);
        }
        break;
    case APP_UPLOADING:
        break;
    }
}

void pollStepIrq() {
    if (!irq) return;
    irq = false;
    while (!sensor->readInterrupt());
    enqueueEvent(EV_STEP_PULSE);
}

void app_handle_event(const AppEvent &e) {
    switch (app.state) {
    case APP_IDLE:
        if (e.type == EV_START) {
            sensor->resetStepCounter();
            app.currentSteps = 0;
            ui_clearSessionArea();
            ui_drawButton(true);
            app.state = APP_COUNTING;
        }
        break;

    case APP_COUNTING:
        if (e.type == EV_STOP) {
            app.previousSteps = sensor->getCounter();
            app.previousDistance = app.previousSteps * 0.0008f;
            ui_showSessionSummary(app.previousSteps, app.previousDistance);
            ui_showUploadPrompt();
            app.state = APP_SESSION_FINISHED;
        } else if (e.type == EV_STEP_PULSE) {
            uint32_t step = sensor->getCounter();
            app.currentSteps = step;
            ui_showStep(step);
            Serial.println(step);
        }
        break;

    case APP_SESSION_FINISHED:
        if (e.type == EV_UPLOAD_SELECTED) {
            if (deviceConnected) {
                sprintf(buffer, "%u", app.previousSteps);
                pTxCharacteristic->setValue(buffer);
                pTxCharacteristic->notify();
                ui_showUploading();
                app.state = APP_UPLOADING;
            } else {
                ui_showNoConnection();
                Serial.println("No device connected, uploading failed.");
                delay(2000);
                ui_showSessionSummary(app.previousSteps, app.previousDistance);
                ui_showUploadPrompt();
                app.state = APP_SESSION_FINISHED;
            }
        } else if (e.type == EV_DISCARD_SESSION) {
            ui_clearSessionArea();
            ui_drawButton(false);
            app.state = APP_IDLE;
        }
        break;

    case APP_UPLOADING:
        if (e.type == EV_UPLOAD_ACK) {
            ui_showUploaded();
            Serial.println("Upload successfully");
            delay(2000);
            ui_clearSessionArea();
            ui_drawTitle();
            ui_drawButton(false);
            app.state = APP_IDLE;
        }
        break;
    }
}

void setup() {
    Serial.begin(115200);
    watch = TTGOClass::getWatch();
    watch->begin();
    watch->openBL();

    tft = watch->tft;
    sensor = watch->bma;
    
    Acfg cfg;
    cfg.odr = BMA4_OUTPUT_DATA_RATE_25HZ;
    cfg.range = BMA4_ACCEL_RANGE_2G;
    cfg.bandwidth = BMA4_ACCEL_NORMAL_AVG4;
    cfg.perf_mode = BMA4_CONTINUOUS_MODE;
    sensor->accelConfig(cfg);
    sensor->enableAccel();
    
    pinMode(BMA423_INT1, INPUT);
    attachInterrupt(BMA423_INT1, stepInterruptHandler, RISING);
    
    sensor->enableFeature(BMA423_STEP_CNTR, true);
    sensor->resetStepCounter();
    sensor->enableStepCountInterrupt();
    
    ui_init(tft);
    ui_drawTitle();
    ui_drawButton(false);

    // BLE Setup
    BLEDevice::init("Hiking Watch");
    pServer = BLEDevice::createServer();
    pServer->setCallbacks(new MyServerCallbacks());
    BLEService *pService = pServer->createService(SERVICE_UUID);
    BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR;

    pTxCharacteristic = pService->createCharacteristic(
        CHARACTERISTIC_UUID_TX, BLECharacteristic::PROPERTY_NOTIFY
    );
    pTxCharacteristic->addDescriptor(new BLE2902());
    
    BLECharacteristic *pRxCharacteristic = pService->createCharacteristic(
        CHARACTERISTIC_UUID_RX, BLECharacteristic::PROPERTY_WRITE
    );
    pRxCharacteristic->setCallbacks(new MyCallbacks());
    
    pService->start();
    BLEAdvertising *pAdvertising = pServer->getAdvertising();
    pAdvertising->setScanResponse(false);
    pAdvertising->setMinPreferred(0x06);
    pAdvertising->start();

    pSecurity->setAuthenticationMode(ESP_LE_AUTH_BOND);

    app.state = APP_IDLE;
    app.currentSteps    = 0;
    app.previousSteps   = 0;
    app.previousDistance = 0.0f;
}

void loop() {
    pollTouch();
    pollStepIrq();

    AppEvent e;
    while (dequeueEvent(e)) {
        app_handle_event(e);
    }
    
    if (!deviceConnected && oldDeviceConnected) {
        delay(500);
        pServer->startAdvertising();
        oldDeviceConnected = deviceConnected;
    }
    
    if (deviceConnected && !oldDeviceConnected) {
        oldDeviceConnected = deviceConnected;
    }

    delay(20);
}
