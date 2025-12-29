#include "events.h"

static const int EVENT_QUEUE_SIZE = 16;
static AppEvent eventQueue[EVENT_QUEUE_SIZE];
static int eventHead = 0;
static int eventTail = 0;

bool enqueueEvent(EventType t) {
    int next = (eventHead + 1) % EVENT_QUEUE_SIZE;
    if (next == eventTail) {
        // 队列已满，丢弃事件
        return false;
    }
    eventQueue[eventHead].type = t;
    eventHead = next;
    return true;
}

bool dequeueEvent(AppEvent &e) {
    if (eventHead == eventTail) {
        return false;
    }
    e = eventQueue[eventTail];
    eventTail = (eventTail + 1) % EVENT_QUEUE_SIZE;
    return true;
}
