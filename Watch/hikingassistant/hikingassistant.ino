#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>
#include "config.h"
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
// #include <BluetoothSerial.h>

// BluetoothSerial SerialBT;

TTGOClass *watch;
TFT_eSPI *tft;
BMA *sensor;
bool irq = false;
bool stepCounting = false;
int16_t x, y;
uint32_t previousSteps = 0;
float previousDistance = 0.0;
char buffer[50];

// BLE Setup
BLEServer *pServer = NULL;
BLECharacteristic *pTxCharacteristic;
BLESecurity *pSecurity = new BLESecurity();
bool deviceConnected = false;
bool oldDeviceConnected = false;

#define SERVICE_UUID "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
#define CHARACTERISTIC_UUID_RX "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
#define CHARACTERISTIC_UUID_TX "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) { deviceConnected = true; }
    void onDisconnect(BLEServer* pServer) { deviceConnected = false; }
};


void successful_print()
{
    tft->fillRoundRect(0, 0, 240, 50, 10, TFT_BLACK);
    tft->setTextColor(TFT_RED);
    tft->setCursor(20, 20);
    tft->print("Uploaded");
    Serial.print("Upload successfully");
}

// void error_print()
// {
//     tft->fillRoundRect(0, 0, 240, 50, 10, TFT_BLACK);
//     tft->setTextColor(TFT_RED);
//     tft->setCursor(20, 20);
//     tft->print("Fail to upload");
//     Serial.print("Fail to upload");
// }

class MyCallbacks: public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pCharacteristic) {
        std::string rxValue = pCharacteristic->getValue();
        if (rxValue.length() > 0) {
            Serial.print("Received Value: ");
            Serial.println(rxValue.c_str());
            if (rxValue == "c") {
                successful_print(); 
                delay(2000);
                drawButton(stepCounting);
            } 
            // else {
            //     error_print();  // 
            // }
        }
    }
};

void drawButton(bool isRunning) {
    tft->fillRoundRect(0, 0, 240, 50, 10, TFT_BLACK);
    tft->fillRoundRect(0, 130, 240, 90, 10, TFT_BLACK);
    tft->fillRoundRect(50, 180, 120, 40, 10, isRunning ? TFT_RED : TFT_GREEN);
    tft->setTextColor(TFT_WHITE);
    tft->setCursor(80, 195);
    tft->print(isRunning ? "STOP" : "START");
}

void uploadChoose(){
    tft->fillRoundRect(0, 130, 240, 90, 10, TFT_BLACK);
    tft->setTextColor(TFT_YELLOW);
    tft->setCursor(20, 130);
    tft->print("Do you want to upload the session?");
    tft->fillRoundRect(20, 180, 100, 40, 10, TFT_BLUE);
    tft->fillRoundRect(120, 180, 100, 40, 10, TFT_PURPLE);
    tft->setTextColor(TFT_WHITE);
    tft->setCursor(20, 195);
    tft->print("UPLOAD");
    tft->setTextColor(TFT_WHITE);
    tft->setCursor(140, 195);
    tft->print("NO");
}

void displayPreviousSession() {
    tft->fillRect(0, 50, 240, 100, TFT_BLACK);
    tft->setTextColor(TFT_WHITE, TFT_BLACK);
    tft->setCursor(20, 60);
    tft->printf("Steps: %d", previousSteps);
    tft->setCursor(20, 90);
    tft->printf("Distance: %.2f km", previousDistance);
}

void IRAM_ATTR stepInterruptHandler() {
    irq = true;
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
    
    tft->setTextFont(4);
    tft->drawString("Hiking Assistant", 3, 50, 4);
    drawButton(stepCounting);

    // BLE Setup
    BLEDevice::init("Hiking Watch");
    pServer = BLEDevice::createServer();
    pServer->setCallbacks(new MyServerCallbacks());
    BLEService *pService = pServer->createService(SERVICE_UUID);
    
    pTxCharacteristic = pService->createCharacteristic(
        CHARACTERISTIC_UUID_TX, BLECharacteristic::PROPERTY_NOTIFY
    );
    pTxCharacteristic->addDescriptor(new BLE2902());
    BLECharacteristic *pRxCharacteristic = pService->createCharacteristic(
        CHARACTERISTIC_UUID_RX, BLECharacteristic::PROPERTY_WRITE
    );
    pRxCharacteristic->setCallbacks(new MyCallbacks());
    
    pService->start();
    pServer->getAdvertising()->start();
    pServer->getAdvertising()->setScanResponse(false);
    pServer->getAdvertising()->setMinPreferred(0x06);
    pSecurity->setAuthenticationMode(ESP_LE_AUTH_BOND);

}


void loop() {
    if (watch->getTouch(x, y)) {
        if (x > 50 && x < 170 && y > 180 && y < 220) {
            stepCounting = !stepCounting;
            if (stepCounting) {
                sensor->resetStepCounter();
                previousSteps = 0;
                previousDistance = 0.0;
                tft->fillRect(0, 50, 240, 100, TFT_BLACK);
            } else {
                previousSteps = sensor->getCounter();
                previousDistance = previousSteps * 0.0008;
                displayPreviousSession();
                uploadChoose();
                delay(500);
                while (1) {
                if(watch->getTouch(x, y))
                {
                  if (x > 20 && x < 120 && y > 180 && y < 220) {
                      if (deviceConnected) {
                        sprintf(buffer, "%d", previousSteps);
                        pTxCharacteristic->setValue(buffer);
                        pTxCharacteristic->notify();
                      }                   
                  }
                  else if (x > 120 && x < 220 && y > 180 && y < 220)  {
                        break;
                  }
                }
                }
                
            }
            drawButton(stepCounting);
            delay(300);
        }
    }
    
    if (irq) {
        irq = false;
        while (!sensor->readInterrupt());
        if (stepCounting) {
            uint32_t step = sensor->getCounter();
            tft->fillRect(45, 118, 200, 20, TFT_BLACK);
            tft->setTextColor(random(0xFFFF), TFT_BLACK);
            tft->setCursor(50, 118);
            tft->print("Steps:");
            tft->print(step);
            Serial.println(step);
        }
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
