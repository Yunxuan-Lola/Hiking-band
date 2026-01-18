#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

#include "inc/config.h"
#include "inc/ui.h"
#include "inc/events.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"

static SemaphoreHandle_t g_sensorMutex = nullptr;
static SemaphoreHandle_t g_appMutex    = nullptr;


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
volatile bool deviceConnected = false;

//volatile bool irq = false;
// Task notification bits (support multiple IRQ sources) 

TaskHandle_t touchTaskHandle = nullptr;
TaskHandle_t stepTaskHandle  = nullptr;
TaskHandle_t bleTaskHandle   = nullptr;

static constexpr uint32_t NOTIF_STEP_IRQ          = (1u << 0);
static constexpr uint32_t NOTIF_TOUCH_IRQ         = (1u << 1);
static constexpr uint32_t NOTIF_APP_EVENT         = (1u << 2); // 任何 app event 入队后唤醒 TouchTask
static constexpr uint32_t NOTIF_BLE_ADV_RESTART   = (1u << 0); // BleTask 用

static inline void notify_touch_task(uint32_t bits) {
    if (touchTaskHandle) {
        xTaskNotify(touchTaskHandle, bits, eSetBits);
    }
}

static inline void notify_ble_task(uint32_t bits) {
    if (bleTaskHandle) {
        xTaskNotify(bleTaskHandle, bits, eSetBits);
    }
}

static inline bool postEvent(EventType t) {
    bool ok = enqueueEvent(t);
    if (ok) notify_touch_task(NOTIF_APP_EVENT);
    return ok;
}

#define SERVICE_UUID "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
#define CHARACTERISTIC_UUID_RX "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
#define CHARACTERISTIC_UUID_TX "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

// class MyServerCallbacks: public BLEServerCallbacks {
//     void onConnect(BLEServer* pServer) { deviceConnected = true; }
//     void onDisconnect(BLEServer* pServer) { deviceConnected = false; }
// };

// class MyCallbacks: public BLECharacteristicCallbacks {
//     void onWrite(BLECharacteristic *pCharacteristic) {
//         std::string rxValue = pCharacteristic->getValue();
//         Serial.print("Received Value: ");
//         Serial.println(rxValue.c_str());
//         if (rxValue == "r") {
//             enqueueEvent(EV_UPLOAD_ACK);
//         }
//     }
// };
class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) override {
        postEvent(EV_BLE_CONNECTED);
    }
    void onDisconnect(BLEServer* pServer) override {
        postEvent(EV_BLE_DISCONNECTED);
    }
};

class MyCallbacks: public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pCharacteristic) override {
        std::string rxValue = pCharacteristic->getValue();
        Serial.print("Received Value: ");
        Serial.println(rxValue.c_str());
        if (rxValue == "r") {
            postEvent(EV_UPLOAD_ACK);
        }
    }
};


// void IRAM_ATTR stepInterruptHandler() {
//     irq = true;
// }
void IRAM_ATTR stepInterruptHandler() {
    BaseType_t hpTaskWoken = pdFALSE;
    if (stepTaskHandle) {
        xTaskNotifyFromISR(stepTaskHandle, NOTIF_STEP_IRQ, eSetBits, &hpTaskWoken);
    }
    if (hpTaskWoken) {
        portYIELD_FROM_ISR();
    }
}

void IRAM_ATTR touchInterruptHandler() {
    BaseType_t hpTaskWoken = pdFALSE;
    if (touchTaskHandle) {
        xTaskNotifyFromISR(touchTaskHandle, NOTIF_TOUCH_IRQ, eSetBits, &hpTaskWoken);
    }
    if (hpTaskWoken) {
        portYIELD_FROM_ISR();
    }
}

static inline bool touchInRect(int16_t tx, int16_t ty, int x0, int y0, int x1, int y1) {
    return (tx > x0 && tx < x1 && ty > y0 && ty < y1);
}

struct UiPlan {
    bool clear_to_idle = false;
    bool start_counting_ui = false;
    bool show_summary = false;
    bool show_prompt = false;
    bool show_uploading = false;
    bool show_no_conn = false;
    bool show_uploaded = false;  

    uint32_t steps = 0;
    float dist = 0.0f;

    bool do_ble_send = false;
    uint32_t ble_steps = 0;
    bool adv_restart = false;
    bool refresh_step = false;
    uint32_t refresh_step_value = 0;
};

static void pollTouchAndPostEvent() {
    if (!watch->getTouch(x, y)) return;
    
    AppState st = APP_IDLE;
    if (g_appMutex && xSemaphoreTake(g_appMutex, pdMS_TO_TICKS(5)) == pdTRUE) {
        st = app.state;
        xSemaphoreGive(g_appMutex);
    } else {
        return;
    }

    switch (st) {
    case APP_IDLE:
    case APP_COUNTING:
        if (touchInRect(x, y, 50, 180, 170, 220)) {
            postEvent(EV_MAIN_BUTTON_PRESSED);
        }
        break;
    case APP_SESSION_FINISHED:
        if (touchInRect(x, y, 20, 180, 120, 220)) {
            postEvent(EV_UPLOAD_YES_PRESSED);
        } else if (touchInRect(x, y, 120, 180, 220, 220)) {            
            postEvent(EV_UPLOAD_NO_PRESSED);
        }
        break;
    case APP_UPLOADING:
        break;
    }
}

// void pollStepIrq() {
//     if (!irq) return;
//     irq = false;
//     while (!sensor->readInterrupt());
//     if (app.state == APP_COUNTING) {
//         uint32_t step = sensor->getCounter();
//         app.currentSteps = step;
//         ui_showStep(step);
//         Serial.println(step);
//     }
// }


static Uiplan app_handle_event(const AppEvent &e) {
    UiPlan plan;

    if (e.type == EV_BLE_CONNECTED) {
        deviceConnected = true;
        return plan;
    }
    if (e.type == EV_BLE_DISCONNECTED) {
        deviceConnected = false;
        plan.adv_restart = true;
        //notify_ble_task(NOTIF_BLE_ADV_RESTART);

        if (app.state == APP_UPLOADING) {
            Serial.println("BLE disconnected during uploading.");
            //ui_showNoConnection();              
            //ui_showSessionSummary(app.previousSteps, app.previousDistance);
            //ui_showUploadPrompt();
            plan.show_no_conn = true;
            plan.show_summary = true;
            plan.show_prompt = true;
            plan.steps = app.previousSteps;
            plan.dist = app.previousDistance;
            app.state = APP_SESSION_FINISHED;
        }
        return plan;
    }

    switch (app.state) {
    case APP_IDLE:
        if (e.type == EV_MAIN_BUTTON_PRESSED) {
            if (g_sensorMutex && xSemaphoreTake(g_sensorMutex, pdMS_TO_TICKS(50)) == pdTRUE) {
                sensor->resetStepCounter();
                xSemaphoreGive(g_sensorMutex);
            }
            //sensor->resetStepCounter();
            app.currentSteps = 0;
            plan.start_counting_ui = true;          ///////
            //ui_clearSessionArea();
            //ui_drawButton(true);
            app.state = APP_COUNTING;
        }
        break;

    case APP_COUNTING:
        if (e.type == EV_MAIN_BUTTON_PRESSED) {
            app.previousSteps = 0;
            if (g_sensorMutex && xSemaphoreTake(g_sensorMutex, pdMS_TO_TICKS(50)) == pdTRUE) {
                app.previousSteps = sensor->getCounter();
                xSemaphoreGive(g_sensorMutex);
            }

            //app.previousSteps = sensor->getCounter();
            app.previousDistance = app.previousSteps * 0.0008f;
            //ui_showSessionSummary(app.previousSteps, app.previousDistance);
            //ui_showUploadPrompt();
            plan.show_summary = true;
            plan.show_prompt = true;
            plan.steps = app.previousSteps;   
            plan.dist  = app.previousDistance;
            app.state = APP_SESSION_FINISHED;
        } 
        break;

    case APP_SESSION_FINISHED:
        if (e.type == EV_UPLOAD_YES_PRESSED) {
            if (deviceConnected) {
                sprintf(buffer, "%u", app.previousSteps);
                pTxCharacteristic->setValue(buffer);
                pTxCharacteristic->notify();

                //plan.do_ble_send = true;
                //plan.ble_steps = app.previousSteps;
                plan.show_uploading = true;
                //ui_showUploading();
                app.state = APP_UPLOADING;
            } else {
                //ui_showNoConnection();
                Serial.println("No device connected, uploading failed.");
                
                plan.show_no_conn = true;
                plan.show_summary = true;
                plan.show_prompt = true;
                plan.steps = app.previousSteps;
                plan.dist  = app.previousDistance;
                //ui_showSessionSummary(app.previousSteps, app.previousDistance);
                //ui_showUploadPrompt();
                app.state = APP_SESSION_FINISHED;
                return;
            }
        } else if (e.type == EV_UPLOAD_NO_PRESSED) {
            //ui_clearSessionArea();
            //ui_drawButton(false);
            plan.clear_to_idle = true;              /////
            app.state = APP_IDLE;
        }
        break;

    case APP_UPLOADING:
        if (e.type == EV_UPLOAD_ACK) {
            //ui_showUploaded();
            Serial.println("Upload successfully");
            //vTaskDelay(pdMS_TO_TICKS(2000));
            //ui_clearSessionArea();
            //ui_drawTitle();
            //ui_drawButton(false);
            plan.show_uploaded = true;
            plan.clear_to_idle = true;
            app.state = APP_IDLE;
        }
        break;
    }
    return plan;
}

static inline void snapshot_for_step_refresh(UiPlan &plan) {
    if (!g_appMutex || xSemaphoreTake(g_appMutex, 0) != pdTRUE) return;
    if (app.state == APP_COUNTING) {
        plan.refresh_step = true;
        plan.refresh_step_value = app.currentSteps;
    }
    xSemaphoreGive(g_appMutex);
}

static void execute_plan_outside_lock(UiPlan &plan) {
    if (plan.adv_restart) notify_ble_task(NOTIF_BLE_ADV_RESTART);

    if (plan.start_counting_ui) {
        if (g_sensorMutex && xSemaphoreTake(g_sensorMutex, pdMS_TO_TICKS(50)) == pdTRUE) {
            sensor->resetStepCounter();
            xSemaphoreGive(g_sensorMutex);
        }
        ui_clearSessionArea();
        ui_drawButton(true);
    }

    if (plan.show_no_conn) ui_showNoConnection();

    if (plan.show_summary) ui_showSessionSummary(plan.steps, plan.dist);
    if (plan.show_prompt)  ui_showUploadPrompt();

    if (plan.do_ble_send) {
        snprintf(buffer, sizeof(buffer), "%u", (unsigned)plan.ble_steps);
        if (pTxCharacteristic) {
            pTxCharacteristic->setValue(buffer);
            pTxCharacteristic->notify();
        }
    }

    if (plan.show_uploading) ui_showUploading();

    if (plan.show_uploaded) {
        ui_showUploaded();
        vTaskDelay(pdMS_TO_TICKS(2000));
    }

    if (plan.clear_to_idle) {
        ui_clearSessionArea();
        ui_drawTitle();
        ui_drawButton(false);
    }

    if (plan.refresh_step) ui_showStep(plan.refresh_step_value);
}
// TaskHandle_t touchTaskHandle = nullptr;
// TaskHandle_t stepTaskHandle       = nullptr;
// TaskHandle_t bleTaskHandle       = nullptr;

// void StepTask(void *arg) {
//     for (;;) {
//         pollStepIrq();
//         vTaskDelay(pdMS_TO_TICKS(5));    
//     }
// }

// void TouchTask(void *arg) {
//     AppEvent e;
//     for (;;) {
//         pollTouch();
//         while (dequeueEvent(e)) {
//             app_handle_event(e);
//         }
//         vTaskDelay(pdMS_TO_TICKS(10));
//     }
// }

void TouchTask(void *arg) {
    AppEvent e;
    for (;;) {
        uint32_t pending = 0;

        // 事件驱动
        xTaskNotifyWait(
            0,
            0xFFFFFFFFu,
            &pending,
            portMAX_DELAY
        );

        if (pending & NOTIF_TOUCH_IRQ) {
            pollTouchAndPostEvent();
        }

        while (dequeueEvent(e)) {
            UiPlan plan;
            if (g_appMutex) xSemaphoreTake(g_appMutex, portMAX_DELAY);
            //app_handle_event(e);
            if (app.state == APP_COUNTING && e.type == EV_MAIN_BUTTON_PRESSED) {
                uint32_t ps = 0;
                if (g_sensorMutex && xSemaphoreTake(g_sensorMutex, pdMS_TO_TICKS(50)) == pdTRUE) {
                    ps = sensor->getCounter();
                    xSemaphoreGive(g_sensorMutex);
                }
                app.previousSteps = ps;
                app.previousDistance = ps * 0.0008f;
            }
            plan = app_handle_event(e);
            if (plan.show_summary) {
                plan.steps = app.previousSteps;
                plan.dist  = app.previousDistance;
            }
            if (plan.do_ble_send) {
                plan.ble_steps = app.previousSteps;
            }

            if (g_appMutex) xSemaphoreGive(g_appMutex);

            execute_plan_outside_lock(plan);
        }
        UiPlan refresh;
        snapshot_for_step_refresh(refresh);
        if (refresh.refresh_step) execute_plan_outside_lock(refresh);
        // if (g_appMutex && xSemaphoreTake(g_appMutex, 0) == pdTRUE) {
        //     if (app.state == APP_COUNTING) ui_showStep(app.currentSteps);
        //     xSemaphoreGive(g_appMutex);
        // }
    }
}

static bool drainStepInterruptWithTimeout(uint32_t maxWaitMs) {
    TickType_t deadline = xTaskGetTickCount() + pdMS_TO_TICKS(maxWaitMs);
    while (!sensor->readInterrupt()) {
        if (xTaskGetTickCount() >= deadline) return false;
        vTaskDelay(pdMS_TO_TICKS(1));
    }
    return true;
}

void StepTask(void *arg) {
    for (;;) {
        uint32_t pending = 0;

        // 等待被置位
        xTaskNotifyWait(
            0,                  // 不在进入时清除任何位
            0xFFFFFFFFu,        // 退出时清除所有已取出的位
            &pending,           // 取出通知值（bit mask）
            portMAX_DELAY
        );

        // 处理步数中断
        if (pending & NOTIF_STEP_IRQ) {
            uint32_t step = 0;
            bool ok = false;

            if (g_sensorMutex && xSemaphoreTake(g_sensorMutex, pdMS_TO_TICKS(20)) == pdTRUE) {
                ok = drainStepInterruptWithTimeout(10);
                if (ok) step = sensor->getCounter();
                xSemaphoreGive(g_sensorMutex);
            }

            if (!ok) {
                Serial.println("WARN: step IRQ notified but sensor->readInterrupt() timeout");
                continue;
            }
            
            bool needWake = false;
            if (g_appMutex && xSemaphoreTake(g_appMutex, pdMS_TO_TICKS(10)) == pdTRUE) {
                if (app.state == APP_COUNTING) {
                    app.currentSteps = step;
                    needWake = true;
                }
                xSemaphoreGive(g_appMutex);
            }
            if (needWake) notify_touch_task(NOTIF_APP_EVENT);
        }
    }
}

void BleTask(void *arg) {
    for (;;) {
        uint32_t pending = 0;
        xTaskNotifyWait(
            0, 
            0xFFFFFFFFu, 
            &pending, 
            portMAX_DELAY
        );

        if (pending & NOTIF_BLE_ADV_RESTART) {
            vTaskDelay(pdMS_TO_TICKS(500));
            if (pServer) {
                pServer->startAdvertising();
            }
        }
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
    
    ui_init(tft);
    ui_drawTitle();
    ui_drawButton(false);

    events_init(16);

    // BLE Setup
    BLEDevice::init("Hiking Watch");
    pServer = BLEDevice::createServer();
    pServer->setCallbacks(new MyServerCallbacks());
    BLEService *pService = pServer->createService(SERVICE_UUID);
    //BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR;

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

    g_sensorMutex = xSemaphoreCreateMutex();
    g_appMutex    = xSemaphoreCreateMutex();

    if (g_appMutex) xSemaphoreTake(g_appMutex, portMAX_DELAY);
    app.state = APP_IDLE;
    app.currentSteps    = 0;
    app.previousSteps   = 0;
    app.previousDistance = 0.0f;
    if (g_appMutex) xSemaphoreGive(g_appMutex);

    xTaskCreate(
        TouchTask,
        "TouchTask",
        4096,
        nullptr,
        2,              // 中
        &touchTaskHandle
    );

    xTaskCreate(
        StepTask,
        "StepTask",
        4096,
        nullptr,
        3,              // 高
        &stepTaskHandle
    );
    xTaskCreate(
        BleTask,
        "BleTask",
        4096,
        nullptr,
        1,              // 低
        &bleTaskHandle
    );
        
    pinMode(BMA423_INT1, INPUT);
    attachInterrupt(BMA423_INT1, stepInterruptHandler, RISING);
    
    pinMode(TOUCH_INT, INPUT_PULLUP);
    attachInterrupt(TOUCH_INT, touchInterruptHandler, FALLING);

    sensor->enableFeature(BMA423_STEP_CNTR, true);
    sensor->resetStepCounter();
    sensor->enableStepCountInterrupt();
}

void loop() {
    vTaskDelay(pdMS_TO_TICKS(1000));
}
