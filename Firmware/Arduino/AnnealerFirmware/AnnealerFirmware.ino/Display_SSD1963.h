#pragma once
// ══════════════════════════════════════════════════════════════════
//  Display_SSD1963.h — Rev3.0 panel bring-up
//
//  Panel      : SATOZ SAT070AT40D21, 7", 800x480, 24-bit parallel RGB,
//               DE-mode timing (see table below)
//  Controller : Solomon Systech SSD1963QL9 on the PCB, 10 MHz crystal,
//               8-bit 8080 host bus to the ESP32 (write only, RD tied high)
//  Library    : TFT_eSPI 2.5.44 with SSD1963_800_DRIVER + TFT_PARALLEL_8_BIT
//               (User_Setup_Rev3.h). tft.init() runs TFT_eSPI's generic
//               SSD1963 800x480 sequence; ssd1963_panel_init() is called
//               right after it and re-programs the clock tree + LCD timing
//               with this panel's datasheet values. Everything is sent with
//               TFT_eSPI's public writecommand()/writedata().
//
//  Panel timing (SAT070AT40D21 typ.):
//      pixel clock 33.3 MHz (max 50)
//      H: 800 active, total 1056 = HBP 46 + 800 + HFP 210, HPW 1..40 → 20
//      V: 480 active, total  525 = VBP 23 + 480 + VFP  22, VPW 1..20 → 10
//  SSD1963 register semantics (set_hori_period 0xB4 / set_vert_period 0xB6):
//      HT  = horizontal total − 1               = 1055
//      HPS = non-display clocks before the active area = HBP = 46
//            (the panel's HBP figure includes the sync pulse)
//      HPW = sync pulse width − 1               = 19
//      LPS = sync pulse start position          = 0 (pulse at line start)
//      VT  = 524, VPS = 23, VPW = 9, FPS = 0   (same scheme, in lines)
//  In DE mode the panel latches on DE only, so HPW/VPW are nominal.
//
//  Clock tree:
//      PLL  = XTAL × (N+1) / (M+1) with VCO = XTAL × (N+1) in 250..800 MHz
//           = 10 MHz × 30 / 3 = 100 MHz            (0xE2: N=0x1D, M=0x02)
//      PCLK = PLL × (LCDC_FPR + 1) / 2^20
//           → FPR = 33.3 MHz / 100 MHz × 2^20 − 1 = 349175 = 0x0553F7
//           → PCLK = 33.30 MHz                     (0xE6: 05 53 F7)
//      Backlight PWM = PLL / (256 × (prescaler + 1)); prescaler 0x0E gives
//      ≈ 26 kHz — above audible, below what most LED driver PWM inputs
//      tolerate. Change SSD_BL_PWM_PRESCALE if your driver wants slower.
// ══════════════════════════════════════════════════════════════════
#include <Arduino.h>
#include <TFT_eSPI.h>

extern TFT_eSPI tft;
extern uint8_t  display_brightness;

#define SSD_HDP   800
#define SSD_VDP   480
#define SSD_HT    1056
#define SSD_HPS   46        // HBP (incl. sync pulse)
#define SSD_HPW   20
#define SSD_LPS   0
#define SSD_VT    525
#define SSD_VPS   23        // VBP (incl. sync pulse)
#define SSD_VPW   10
#define SSD_FPS   0
#define SSD_PLL_N 0x1D      // VCO = 10 MHz × 30 = 300 MHz
#define SSD_PLL_M 0x02      // PLL = 300 / 3 = 100 MHz
#define SSD_FPR   0x0553F7  // 33.3 MHz pixel clock from a 100 MHz PLL
#define SSD_BL_PWM_PRESCALE 0x0E

// Backlight duty 0..255 through the SSD1963's PWM output (set_pwm_conf).
// DBC (dynamic backlight control) is disabled in ssd1963_panel_init(), so
// the duty written here is exactly what the backlight driver sees.
static inline void ssd1963_set_brightness(uint8_t duty) {
  tft.writecommand(0xBE);
  tft.writedata(SSD_BL_PWM_PRESCALE); // PWM frequency prescaler
  tft.writedata(duty);                // PWM duty 0..255
  tft.writedata(0x01);                // bit0 = PWM enable, bit3 = 0 → host controlled
  tft.writedata(0xFF);                // DBC manual brightness (unused, DBC off)
  tft.writedata(0x00);                // DBC minimum brightness
  tft.writedata(0x00);                // brightness prescaler (DBC)
}

// Full re-initialisation of the SSD1963 for the SAT070AT40D21. Mirrors the
// structure of TFT_eSPI's SSD1963_Init.h (PLL → soft reset → PCLK → LCD
// mode → porches → bus width → display on) with this panel's numbers.
// Call after tft.init() and before tft.setRotation().
static void ssd1963_panel_init() {
  // --- PLL: 100 MHz from the 10 MHz crystal --------------------------------
  tft.writecommand(0xE2);             // set_pll_mn
  tft.writedata(SSD_PLL_N);
  tft.writedata(SSD_PLL_M);
  tft.writedata(0x04);                // "effectuate" the multiplier/divider
  tft.writecommand(0xE0);             // set_pll: enable
  tft.writedata(0x01);
  delay(10);                          // PLL lock (>100 µs)
  tft.writecommand(0xE0);             // set_pll: use PLL as system clock
  tft.writedata(0x03);
  delay(10);

  tft.writecommand(0x01);             // soft reset, now running from the PLL
  delay(100);

  // --- Pixel clock -----------------------------------------------------------
  tft.writecommand(0xE6);             // set_lshift_freq
  tft.writedata((SSD_FPR >> 16) & 0x0F);
  tft.writedata((SSD_FPR >>  8) & 0xFF);
  tft.writedata( SSD_FPR        & 0xFF);

  // --- LCD mode: 24-bit TFT panel, 800x480 ---------------------------------
  tft.writecommand(0xB0);             // set_lcd_mode
  tft.writedata(0x20);                // A: bit5 = 24-bit panel data width,
                                      //    no dithering/FRC, default polarities
  tft.writedata(0x00);                // B: TFT mode, Hsync+Vsync+DE output
  tft.writedata(((SSD_HDP - 1) >> 8) & 0xFF);
  tft.writedata( (SSD_HDP - 1)       & 0xFF);
  tft.writedata(((SSD_VDP - 1) >> 8) & 0xFF);
  tft.writedata( (SSD_VDP - 1)       & 0xFF);
  tft.writedata(0x00);                // G: even/odd line RGB sequence = RGB

  // --- Horizontal timing -----------------------------------------------------
  tft.writecommand(0xB4);             // set_hori_period
  tft.writedata(((SSD_HT - 1) >> 8) & 0xFF);
  tft.writedata( (SSD_HT - 1)       & 0xFF);
  tft.writedata((SSD_HPS >> 8) & 0xFF);
  tft.writedata( SSD_HPS       & 0xFF);
  tft.writedata((SSD_HPW - 1)  & 0x7F);
  tft.writedata((SSD_LPS >> 8) & 0xFF);
  tft.writedata( SSD_LPS       & 0xFF);
  tft.writedata(0x00);                // LPSPP (serial RGB only)

  // --- Vertical timing -------------------------------------------------------
  tft.writecommand(0xB6);             // set_vert_period
  tft.writedata(((SSD_VT - 1) >> 8) & 0xFF);
  tft.writedata( (SSD_VT - 1)       & 0xFF);
  tft.writedata((SSD_VPS >> 8) & 0xFF);
  tft.writedata( SSD_VPS       & 0xFF);
  tft.writedata((SSD_VPW - 1)  & 0x3F);
  tft.writedata((SSD_FPS >> 8) & 0xFF);
  tft.writedata( SSD_FPS       & 0xFF);

  // --- Host interface: 8-bit bus → RGB 8:8:8, three writes per pixel -------
  tft.writecommand(0xF0);             // set_pixel_data_interface
  tft.writedata(0x00);

  // --- SSD1963 GPIO0 as "LCD ON" like the TFT_eSPI init does ----------------
  tft.writecommand(0xB8);             // set_gpio_conf
  tft.writedata(0x0F);                // GPIO[3:0] outputs
  tft.writedata(0x01);                // GPIO0 normal
  tft.writecommand(0xBA);             // set_gpio_value
  tft.writedata(0x01);                // GPIO0 = 1

  // --- Backlight: DBC off, manual PWM --------------------------------------
  tft.writecommand(0xD0);             // set_dbc_conf
  tft.writedata(0x00);                // DBC disabled → brightness purely manual
  ssd1963_set_brightness(display_brightness);

  tft.writecommand(0x29);             // display on
  // MADCTL (rotation / colour order) is written by tft.setRotation().
}
