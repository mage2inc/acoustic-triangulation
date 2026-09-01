#include <Arduino.h>
#define LED 48
static void show(uint8_t r,uint8_t g,uint8_t b){ rgbLedWrite(LED,g,r,b); } // RGB-order swap
void setup(){ Serial.begin(115200); }
void loop(){
  show(60,0,0); delay(400);   // red
  show(0,0,60); delay(400);   // blue
  show(60,0,60); delay(400);  // magenta
  show(0,0,0);   delay(200);
}
