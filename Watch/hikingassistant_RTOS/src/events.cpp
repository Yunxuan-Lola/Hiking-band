#include "../inc/events.h"
#include <Arduino.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>

static QueueHandle_t eventQueue = nullptr;

void events_init(unsigned size) {
    eventQueue = xQueueCreate(size, sizeof(AppEvent));
}

bool enqueueEvent(EventType t) {
    AppEvent event = {t};
    return eventQueue && xQueueSend(eventQueue, &event, 0) == pdTRUE;
}

bool dequeueEvent(AppEvent &e) {
    return eventQueue && xQueueReceive(eventQueue, &e, 0) == pdTRUE;
}
