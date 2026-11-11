#pragma once
#include <stdint.h>

enum AppState {
    APP_IDLE,
    APP_COUNTING,
    APP_SESSION_FINISHED,
    APP_UPLOADING
};

enum EventType {
    EV_NONE = 0,
    EV_BLE_CONNECTED,
    EV_BLE_DISCONNECTED,
    EV_MAIN_BUTTON_PRESSED,
    EV_UPLOAD_YES_PRESSED,
    EV_UPLOAD_NO_PRESSED,
    EV_START,
    EV_STOP,
    EV_UPLOAD_SELECTED,
    EV_DISCARD_SESSION,
    EV_STEP_PULSE,
    EV_UPLOAD_ACK
};

struct AppEvent {
    EventType type;
};

struct AppContext {
    AppState  state;
    uint32_t  currentSteps;
    uint32_t  previousSteps;
    float     previousDistance;
};

bool enqueueEvent(EventType t);
bool dequeueEvent(AppEvent &e);
void events_init(unsigned size);
