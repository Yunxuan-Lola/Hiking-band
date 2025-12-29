#pragma once
#include <stdint.h>
#include <TFT_eSPI.h>

void ui_init(TFT_eSPI *display);
void ui_drawTitle();
void ui_drawButton(bool running);
void ui_clearSessionArea();
void ui_showSessionSummary(uint32_t steps, float distanceKm);
void ui_showUploading();
void ui_showNoConnection();
void ui_showUploadPrompt();
void ui_showStep(uint32_t step);
void ui_showUploaded();
