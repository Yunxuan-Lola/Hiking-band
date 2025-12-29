#include <Arduino.h>
#include "ui.h"

static TFT_eSPI *tft = nullptr;

void ui_init(TFT_eSPI *display) {
    tft = display;
    tft->setTextFont(4);
    tft->fillScreen(TFT_BLACK);
}

void ui_drawTitle() {
    tft->drawString("Hiking Assistant", 3, 50, 4);
}

void ui_drawButton(bool running) {
    tft->fillRoundRect(0, 0, 240, 50, 10, TFT_BLACK);
    tft->fillRoundRect(0, 130, 240, 90, 10, TFT_BLACK);
    tft->fillRoundRect(50, 180, 120, 40, 10, running ? TFT_RED : TFT_GREEN);
    tft->setTextColor(TFT_WHITE);
    tft->setCursor(80, 195);
    tft->print(running ? "STOP" : "START");
}

void ui_clearSessionArea() {
    tft->fillRect(0, 50, 240, 100, TFT_BLACK);
}

void ui_showSessionSummary(uint32_t steps, float distanceKm) {
    tft->fillRect(0, 50, 240, 100, TFT_BLACK);
    tft->setTextColor(TFT_WHITE, TFT_BLACK);
    tft->setCursor(20, 60);
    tft->printf("Steps: %u", steps);
    tft->setCursor(20, 90);
    tft->printf("Distance: %.2f km", distanceKm);
}

void ui_showUploadPrompt() {
    tft->fillRoundRect(0, 130, 240, 90, 10, TFT_BLACK);
    tft->setTextColor(TFT_YELLOW);
    tft->setCursor(20, 130);
    tft->print("Upload this session?");
    tft->fillRoundRect(20, 180, 100, 40, 10, TFT_BLUE);
    tft->fillRoundRect(120, 180, 100, 40, 10, TFT_PURPLE);
    tft->setTextColor(TFT_WHITE);
    tft->setCursor(30, 195);
    tft->print("UPLOAD");
    tft->setCursor(150, 195);
    tft->print("NO");
}

void ui_showUploading() {
    // 覆盖原来的上传选项区域，显示“上传中”状态
    tft->fillRoundRect(0, 130, 240, 90, 10, TFT_BLACK);
    tft->setTextColor(TFT_CYAN);
    tft->setCursor(40, 160);
    tft->print("Uploading...");
}

void ui_showNoConnection() {
    // 覆盖底部区域，提示当前没有 BLE 连接
    tft->fillRoundRect(0, 130, 240, 90, 10, TFT_BLACK);
    tft->setTextColor(TFT_RED);
    tft->setCursor(20, 160);
    tft->print("No BLE connection");
}

void ui_showStep(uint32_t step) {
    tft->fillRect(45, 118, 200, 20, TFT_BLACK);
    tft->setTextColor(random(0xFFFF), TFT_BLACK);
    tft->setCursor(50, 118);
    tft->print("Steps:");
    tft->print(step);
}

void ui_showUploaded() {
    tft->fillRoundRect(0, 0, 240, 50, 10, TFT_BLACK);
    tft->setTextColor(TFT_RED);
    tft->setCursor(20, 20);
    tft->print("Uploaded");
}
