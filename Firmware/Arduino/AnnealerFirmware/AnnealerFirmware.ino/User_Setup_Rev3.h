// ══════════════════════════════════════════════════════════════════
//  User_Setup_Rev3.h — TFT_eSPI 2.5.44 configuration for hardware Rev3.0
//
//  Rev3.0 drives a 7" 800x480 SATOZ SAT070AT40D21 through a Solomon
//  SSD1963QL9 on the PCB. The ESP32 talks to the SSD1963 over an 8-bit
//  8080 parallel bus (TFT_eSPI "ESP32 parallel" mode). This file IS the
//  User_Setup for that build.
//
//  HOW TO INSTALL (TFT_eSPI reads its setup from inside the library):
//    Option A — simplest: copy this file over
//        <sketchbook>/libraries/TFT_eSPI/User_Setup.h
//    Option B — keep several setups: copy it to
//        <sketchbook>/libraries/TFT_eSPI/User_Setups/Setup_Annealer_Rev3.h
//      and in <sketchbook>/libraries/TFT_eSPI/User_Setup_Select.h comment
//      out `#include <User_Setup.h>` and add
//        #include <User_Setups/Setup_Annealer_Rev3.h>
//    Option C — command line / PlatformIO: pass
//        -DUSER_SETUP_LOADED=1 -include "<path>/User_Setup_Rev3.h"
//      (this is how the firmware was compile-checked with arduino-cli).
//
//  Pin map (fixed by the Rev3.0 PCB, do not change):
//    D0=IO16 D1=IO17 D2=IO18 D3=IO19 D4=IO21 D5=IO22 D6=IO23 D7=IO25
//    WR=IO26  DC=IO27  CS=IO5  RST=IO14 (shared with the GT911 touch)
//    RD = not connected to the ESP32 (tied high on the board)
//
//  Notes
//   • TFT_eSPI's ESP32 parallel driver needs DC, WR and D0..D7 on GPIO 0-31
//     so one register write sets the whole bus — all Rev3.0 pins qualify.
//   • TFT_RD is simply NOT defined: TFT_eSPI then defines it as -1 itself,
//     skips the RD pinMode and read-back functions degrade to dummies. No
//     placeholder GPIO is needed (the library does not insist on an RD pin).
//   • TFT_RST is -1 ON PURPOSE. The reset line is shared with the GT911 and
//     is pulsed once by TAMC_GT911::begin() (with INT held low so the touch
//     controller comes up at 0x5D). TFT_eSPI then uses its software reset.
//   • SSD1963_800_DRIVER selects TFT_eSPI's generic 480x800 SSD1963 init;
//     the sketch re-programs PLL / pixel clock / porches for the SAT070AT40D21
//     afterwards (Display_SSD1963.h). The library's own 8-bit-bus SSD1963
//     path expands RGB565 to RGB888 (3 writes per pixel) as the panel needs.
//   • Colour order: if red and blue come out swapped on the panel, change
//     TFT_RGB_ORDER below to TFT_RGB.
// ══════════════════════════════════════════════════════════════════
#define USER_SETUP_ID   300
#define USER_SETUP_INFO "Annealer_Rev3_SSD1963_Parallel"

// ---- Interface / driver --------------------------------------------------
#define TFT_PARALLEL_8_BIT          // ESP32 8-bit 8080 bus
#define SSD1963_800_DRIVER          // 480 x 800 controller, used in landscape via setRotation(1)
#define TFT_RGB_ORDER TFT_BGR       // swap to TFT_RGB if R/B are exchanged on the panel

// ---- Pins (Rev3.0 PCB) ---------------------------------------------------
#define TFT_CS    5
#define TFT_DC   27                 // must be 0-31
#define TFT_RST  -1                 // shared reset is driven by the GT911 init, see notes
#define TFT_WR   26                 // must be 0-31
// #define TFT_RD  -1               // intentionally undefined (RD not connected)

#define TFT_D0   16                 // data bus, all must be 0-31
#define TFT_D1   17
#define TFT_D2   18
#define TFT_D3   19
#define TFT_D4   21
#define TFT_D5   22
#define TFT_D6   23
#define TFT_D7   25

// ---- Fonts ---------------------------------------------------------------
// LVGL renders all text; TFT_eSPI's own fonts are unused. Load only the
// smallest one so the library compiles, and skip SMOOTH_FONT (SPIFFS).
#define LOAD_GLCD
// #define LOAD_FONT2
// #define LOAD_FONT4
// #define LOAD_FONT6
// #define LOAD_FONT7
// #define LOAD_FONT8
// #define LOAD_GFXFF
// #define SMOOTH_FONT

// SPI_FREQUENCY etc. are irrelevant in parallel mode.

// ---- arduino-esp32 3.x compatibility shim ---------------------------------
// ESP-IDF 5 (arduino-esp32 core 3.x) removed the legacy gpio_input_get()
// helper, but TFT_eSPI 2.5.44's ESP32 parallel read path
// (Processors/TFT_eSPI_ESP32.c, readByte()) still calls it, which breaks the
// library compile with "'gpio_input_get' was not declared". This setup file
// is included before that code, so mapping it to the equivalent GPIO input
// register read fixes the build without touching the library. readByte() is
// only used by the (unused here) read-back functions anyway — RD is not
// even wired on Rev3.0.
#if defined(ESP32) && !defined(gpio_input_get)
  #include "soc/gpio_struct.h"
  #define gpio_input_get() (GPIO.in)
#endif
