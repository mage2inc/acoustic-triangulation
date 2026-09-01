// lora_radio.h — one place that hides the SX127x vs SX126x family difference.
// Include this instead of declaring the radio yourself; call lora_begin() in setup().
// Everything else (transmit/receive/readData/startReceive/setPacketReceivedAction/
// getRSSI/getSNR) is identical across families via RadioLib's base class.

#pragma once
#include <RadioLib.h>
#include "node_config.h"

#if defined(LORA_FAMILY_SX126X)
  // LLCC68 / SX1262 (RYLR689): NSS, DIO1 (IRQ), RST, BUSY
  static LLCC68 radio = new Module(PIN_LORA_NSS, PIN_LORA_DIO1, PIN_LORA_RST, PIN_LORA_BUSY);
  #if defined(LORA_RFSW_MANUAL)
    // RYLR689 antenna switch — host drives both control lines (datasheet pins 9/8):
    //   RX: V1=1,V2=0    TX: V1=0,V2=1    idle: 0,0
    static const uint32_t lora_rfsw_pins[] =
      { PIN_LORA_RFSW1, PIN_LORA_RFSW2, RADIOLIB_NC, RADIOLIB_NC, RADIOLIB_NC };
    static const Module::RfSwitchMode_t lora_rfsw_table[] = {
      { Module::MODE_IDLE, { LOW,  LOW  } },
      { Module::MODE_RX,   { HIGH, LOW  } },
      { Module::MODE_TX,   { LOW,  HIGH } },
      END_OF_MODE_TABLE,
    };
  #endif
  static inline int lora_begin() {
  #if defined(LORA_RFSW_MANUAL)
    radio.setRfSwitchTable(lora_rfsw_pins, lora_rfsw_table);
  #endif
    // SX126x begin: freq, bw, sf, cr, syncWord, power, preamble, tcxoVoltage, useLDO
    return radio.begin(LORA_FREQ, LORA_BW, LORA_SF, LORA_CR, LORA_SYNCWORD,
                       LORA_POWER, LORA_PREAMBLE, LORA_TCXO_V, false);
  }
#else
  // SX1276 (XL1276-P01) or SX1278 (433): NSS, DIO0 (IRQ), RST
  static LORA_CHIP radio = new Module(PIN_LORA_NSS, PIN_LORA_DIO0, PIN_LORA_RST, RADIOLIB_NC);
  static inline int lora_begin() {
    return radio.begin(LORA_FREQ, LORA_BW, LORA_SF, LORA_CR, LORA_SYNCWORD,
                       LORA_POWER, LORA_PREAMBLE);
  }
#endif
