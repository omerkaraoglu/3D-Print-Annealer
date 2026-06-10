/*
 * ══════════════════════════════════════════════════════════════════
 *  Advanced 3D-Print Annealer — Firmware with LVGL Touchscreen UI
 *  ESP32 / Arduino Core 3.x / LVGL v8.4 / TFT_eSPI
 * ══════════════════════════════════════════════════════════════════
 *
 *  Hardware (shared VSPI bus: SCK=18, MOSI=23, MISO=19):
 *    ILI9341 display  CS=15  DC=2  RST=4
 *    XPT2046 touch    CS=21
 *    MAX6675 thermo   CS=13   (SCK+MISO shared)
 *    Triac gate       IO33
 *    ZCD input        IO34
 *
 *  External library configuration required:
 *    - TFT_eSPI/User_Setup.h  : ILI9341, SCK=18, MOSI=23, MISO=19,
 *                               CS=15, DC=2, RST=4
 *    - lvgl/lv_conf.h         : LV_COLOR_DEPTH=16, enable LV_USE_*
 *
 *  The original serial command interface is preserved verbatim
 *  (TUNE / LEARN / SET / RAMP / PROFILE: / LAMBDA / PLANT).
 *  The touchscreen calls the same internal code paths.
 *
 *  Screenshot capture for product photography:
 *    SHOT       — dump the currently-displayed screen over serial.
 *    SHOT ALL   — cycle every built screen, dumping each.
 *    Decode with ../screenshot.py (pyserial + Pillow). See that
 *    file's docstring for the full workflow.
 * ══════════════════════════════════════════════════════════════════ */

#include <SPI.h>
#include <Preferences.h>
#include <TFT_eSPI.h>
#include <lvgl.h>
#include <XPT2046_Touchscreen.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include "esp32_cert_bundle.h"
#include <HTTPClient.h>
#include <HTTPUpdate.h>

LV_FONT_DECLARE(lv_font_inter_12);
LV_FONT_DECLARE(lv_font_inter_14);
LV_FONT_DECLARE(lv_font_inter_16);
LV_FONT_DECLARE(lv_font_inter_24);

// ---- OTA / WiFi configuration -------------------------------------------
// Bump this every time you build a new firmware. The check compares this
// against the "version" field of the server's JSON manifest.
#define FIRMWARE_VERSION   "2.1.2"
// HTTP URL of the version manifest JSON. Plain HTTP is easiest; HTTPS works
// too if you switch to WiFiClientSecure and supply the server's root CA.
// Manifest format: { "version": "1.2.3", "url": "http://host/firmware.bin" }
#define OTA_MANIFEST_URL   "https://omerkaraoglu.github.io/3D-Print-Annealer/Firmware/OTA/version.json"

// We verify TLS using the ESP-IDF certificate bundle that arduino-esp32 v3.x
// links into the firmware. It contains ~150 common root CAs (DigiCert,
// Sectigo / USERTrust, Let's Encrypt / ISRG, GlobalSign, Amazon, …) — so we
// stay valid no matter which CA GitHub rotates to.
//
// The bundle binary is exposed by the build with this exact symbol name.
// If a future arduino-esp32 release renames it the linker will tell us.


// ══════════════════════════════════════════════════════════════════
//   SECTION 1 — PIN DEFINITIONS
// ══════════════════════════════════════════════════════════════════
#define TRIAC_PIN   33
#define ZCD_PIN     34
#define CS_PIN      13          // MAX6675 chip-select
#define FAN_PIN     12          // Fan relay
#define TOUCH_CS    21

#define SCREEN_W    320
#define SCREEN_H    240

// ══════════════════════════════════════════════════════════════════
//   SECTION 2 — HARDWARE OBJECTS
// ══════════════════════════════════════════════════════════════════
TFT_eSPI              tft = TFT_eSPI();
XPT2046_Touchscreen   ts(TOUCH_CS);
Preferences           preferences;

// ══════════════════════════════════════════════════════════════════
//   SECTION 3 — CONTROL GLOBALS (unchanged from original)
// ══════════════════════════════════════════════════════════════════
volatile float pid_output = 0.0;

#define MEDIAN_WINDOW 5
float temp_buffer[MEDIAN_WINDOW];
int   buffer_index = 0;
bool  buffer_filled = false;
float current_temp = 0.0;
const float EMA_ALPHA = 0.1;
unsigned long last_temp_read = 0;
unsigned long last_telemetry_time = 0;

#define SLOPE_WINDOW 60
float temp_history[SLOPE_WINDOW];
int   history_index = 0;
bool  history_filled = false;

#define POWER_BUFFER_SIZE 900
float power_history[POWER_BUFFER_SIZE];
int   power_history_index = 0;

unsigned long last_history_time = 0;
float current_slope = 0.0;
float predicted_temp = 0.0;

#define NCR_LUT_SIZE 37
float ncr_lut_heat[NCR_LUT_SIZE];
float ncr_saved_heat[NCR_LUT_SIZE];
float ncr_lut_cool[NCR_LUT_SIZE];
float ncr_saved_cool[NCR_LUT_SIZE];
float ncr_lin_heat[NCR_LUT_SIZE];
float ncr_lin_cool[NCR_LUT_SIZE];
bool  ncr_nvs_heat[NCR_LUT_SIZE];
bool  ncr_nvs_cool[NCR_LUT_SIZE];

// Raw learned NCR from prototype_1 sweep (20..200 °C, 5 °C steps)
// Buckets without learned data use 0 so linearizeNCR() will interpolate them
static const float NCR_DEFAULT_HEAT[NCR_LUT_SIZE] = {
  0.000000f, 0.000536f, 0.002452f, 0.005874f, 0.003987f, 0.005721f, 0.009235f, 0.010331f,
  0.009895f, 0.012373f, 0.011361f, 0.015502f, 0.011804f, 0.017765f, 0.018578f, 0.022075f,
  0.023933f, 0.019671f, 0.023189f, 0.027764f, 0.022931f, 0.026879f, 0.025739f, 0.027236f,
  0.030697f, 0.032321f, 0.030131f, 0.028257f, 0.031236f, 0.029625f, 0.030799f, 0.032442f,
  0.030475f, 0.032322f, 0.029798f, 0.036016f, 0.000000f,
};
static const float NCR_DEFAULT_COOL[NCR_LUT_SIZE] = {
  0.000000f, 0.007521f, 0.000000f, 0.000000f, 0.000000f, 0.003718f, 0.010883f, 0.010430f,
  0.013222f, 0.013421f, 0.000000f, 0.015848f, 0.017784f, 0.021740f, 0.019994f, 0.000000f,
  0.024905f, 0.000000f, 0.028881f, 0.027218f, 0.000000f, 0.000000f, 0.000000f, 0.000000f,
  0.000000f, 0.000000f, 0.000000f, 0.000000f, 0.000000f, 0.000000f, 0.000000f, 0.000000f,
  0.000000f, 0.000000f, 0.000000f, 0.000000f, 0.000000f,
};

int   ncr_active_bucket = -1;
float ncr_prev_ema = 0.0;
unsigned long ncr_stable_start_ms = 0;

float setpoint = 20.0;
float current_setpoint = 20.0;
float ramp_rate_per_sec = 0.0;
bool  is_ramping = false;

float error_integral = 0.0;
float Kc = 1.0, Ti = 100.0;
bool  flatThresholdFlag = 1;
bool  prev_flat_flag = false;

int   tune_state = 0;
float tune_start_temp = 0.0;
unsigned long tune_start_time_ms = 0;
float temp_at_theta = 0.0;
unsigned long time_at_theta_ms = 0;
float tune_step_power = 0.3;

float mpc_tau_c = 40.0f;         // Desired time constant in seconds. Lower = more aggressive climb.
float mpc_error_integral = 0.0f; // Stores the disturbance correction
float mpc_Ki = 0.005f;           // Very weak gain, strictly for fixing model mismatch at steady-state

int   learn_state = 0;
int   learn_target_bucket = 0;
int   learn_start_bucket = 0;
float learn_room_temp = 20.0;
float learn_stable_temp = 20.0;
unsigned long learn_stable_start_ms = 0;
unsigned long learn_observe_start_ms = 0;
float learn_ncr_snapshot = 0.0;

#define LEARN_OBS_WINDOW 90
float learn_obs_temps[LEARN_OBS_WINDOW];
int   learn_obs_count = 0;
float learn_prev_fitted_slope = 0.0;
unsigned long learn_obs_last_sample_ms = 0;

#define PROFILE_MAX_STEPS 16
struct ProfileStep {
  bool is_ramp;
  float target;
  float rate_per_sec;
  unsigned long hold_sec;
};
ProfileStep profile_steps[PROFILE_MAX_STEPS];
int   profile_step_count = 0;
int   profile_current_step = 0;
int   profile_state = 0;
unsigned long profile_hold_start_ms = 0;
// For the final cooldown step: time at which current_temp first entered the
// 20–40 °C "ambient" band while still waiting for arrival. Reset to 0 the
// instant it leaves the band. Once 30 min in-band has elapsed we accept
// that the oven won't cool any further and declare the step complete.
unsigned long profile_ambient_stable_since_ms = 0;
#define PROFILE_AMBIENT_BAND_LO  20.0f
#define PROFILE_AMBIENT_BAND_HI  40.0f
#define PROFILE_AMBIENT_WAIT_MS  (30UL * 60UL * 1000UL)
unsigned long profile_start_ms = 0;
unsigned long profile_plot_last_ms = 0;

float plant_K = 0.0;
float plant_tau = 0.0;
float plant_theta = 0.0;
float lambda_val = 3.0;

// ══════════════════════════════════════════════════════════════════
//   SECTION 4 — UI GLOBALS + COLOR PALETTE
// ══════════════════════════════════════════════════════════════════
// Themed-button role (declared here so Arduino's auto-generated
// prototypes at the top of the .ino can see the type).
enum BtnRole { ROLE_PRIMARY, ROLE_SECONDARY, ROLE_SUCCESS, ROLE_DANGER, ROLE_NEUTRAL, ROLE_AMBER };

// Professional dark palette — used throughout every screen.
#define CLR_BG        0x0B1118
#define CLR_TOP_BAR   0x101010
#define CLR_PANEL     0x141B24
#define CLR_PANEL2    0x1C2530
#define CLR_BORDER    0x2C3540
#define CLR_GRID      0x222C38
#define CLR_TXT       0xDCE3EA
#define CLR_TXT_DIM   0x7A8896
#define CLR_TXT_FAINT 0x4A5666
#define CLR_ACCENT    0x00B4C8   // teal — primary
#define CLR_ACCENT_D  0x00788B   // dark teal — pressed / secondary accent
#define CLR_AMBER     0xE8A83C
#define CLR_AMBER_D   0x6A4A10
#define CLR_DANGER    0xD04848
#define CLR_DANGER_D  0x6A2020
#define CLR_SUCCESS   0x3CA656
#define CLR_SUCCESS_D 0x204A2A
#define CLR_NEUTRAL   0x3A4554
#define CLR_PLANNED   0x6FC5D4   // planned-trajectory line (light teal)
#define CLR_ACTUAL    0xE8A83C   // actual-temp line (amber)

// LVGL display buffers (20-line double buffer)
static lv_disp_draw_buf_t lvDrawBuf;
static lv_color_t lvBuf1[SCREEN_W * 20];
static lv_color_t lvBuf2[SCREEN_W * 20];

// Touch calibration (fallback defaults, stored in NVS)
int16_t ts_min_x = 300, ts_max_x = 3800;
int16_t ts_min_y = 300, ts_max_y = 3800;

// Graph — 120 samples. Rolling 60-min history in idle mode (30 s/sample),
// time-based planned-vs-actual overlay in profile mode.
#define GRAPH_SAMPLES   120
#define GRAPH_PERIOD_MS 30000UL
unsigned long last_graph_sample_ms = 0;

// Planned trajectory (precomputed on profile start)
float profile_planned[GRAPH_SAMPLES];
float profile_total_duration_s = 0.0f;
bool  profile_has_plan = false;
int   profile_last_slot_filled = -1;

// Raised by the control code when a profile completes naturally; consumed
// by ui_update() the next time it runs so the popup is created from the
// LVGL / UI context, not from inside the PID step.
volatile bool profile_completed_popup_pending = false;

// Screens
static lv_obj_t *scrMain          = NULL;
static lv_obj_t *scrMaterial      = NULL;
static lv_obj_t *scrHousehold     = NULL;
static lv_obj_t *scrEngineer      = NULL;
static lv_obj_t *scrCustom        = NULL;
static lv_obj_t *scrCustomDetail  = NULL;
static lv_obj_t *scrBuilder       = NULL;
static lv_obj_t *scrAddType       = NULL;
static lv_obj_t *scrKeypad        = NULL;
static lv_obj_t *scrSettings      = NULL;
static lv_obj_t *scrCalibrate     = NULL;
static lv_obj_t *scrRename        = NULL;
static lv_obj_t *scrWifi          = NULL;
static lv_obj_t *scrOTA           = NULL;
static lv_obj_t *barOTA           = NULL;
static lv_obj_t *lblOTAStatus     = NULL;
static lv_obj_t *lblOTAVersions   = NULL;

// ── Screenshot subsystem ────────────────────────────────────────────
// USB-CDC framebuffer dump for marketing/website shots. Triggered by the
// SHOT (current screen) or SHOT ALL (cycle every screen) serial command.
// While active, my_disp_flush mirrors every tile out the serial port as
// text-framed binary (RGB565 LE, matches LV_COLOR_DEPTH=16). A host
// Python tool reassembles tiles into PNGs.
// Wire-format example for one frame:
//   <<SHOT_BEGIN w=320 h=240 fmt=rgb565_le name=main>>\r\n
//   <<SHOT_TILE x=0 y=0 w=320 h=20 bytes=12800>>\r\n
//   <12800 raw bytes>\r\n
//   ...more tiles...
//   <<SHOT_END>>\r\n
static volatile bool g_shot_active = false;
// Forward declarations — Arduino's prototype generator skips `static`
// functions, and handleCommand() calls into the capture helper that's
// defined further down the file.
static const char *current_screen_name();
static void        screenshot_capture_current();

// WiFi credentials — persisted in the "wifi" NVS namespace.
static char   wifi_ssid[33] = "";
static char   wifi_pass[65] = "";
static bool   wifi_connected_flag = false;

// Scan results — stage-1 list picker.
#define WIFI_SCAN_MAX     24
#define WIFI_LIST_VISIBLE 8                 // rows shown at once on screen
struct WifiScanEntry {
  char    ssid[33];
  int8_t  rssi;
  uint8_t enc;
};
static WifiScanEntry wifi_scan_results[WIFI_SCAN_MAX];
static int  wifi_scan_count       = 0;
static int  wifi_sel_idx          = 0;     // highlighted row (display-list index)
static int  wifi_list_top         = 0;     // first visible row (display-list index)
static bool wifi_scan_in_progress = false;

// Saved networks — multiple credentials stored in the "wifi" NVS namespace.
// On boot the first slot is also copied into wifi_ssid/wifi_pass so the
// auto-reconnect path keeps working unchanged.
#define SAVED_NET_MAX 8
struct SavedNetwork {
  char ssid[33];
  char pass[65];
};
static SavedNetwork saved_nets[SAVED_NET_MAX];
static int saved_net_count = 0;

// Merged display list: saved networks first (always shown, with in_range
// flagged), then scan-only entries deduped against saved by SSID.
#define WIFI_DISPLAY_MAX (WIFI_SCAN_MAX + SAVED_NET_MAX)
struct WifiDisplayEntry {
  const char *ssid;     // points at either saved_nets[].ssid or wifi_scan_results[].ssid
  bool        is_saved;
  bool        in_range;
  int8_t      rssi;
};
static WifiDisplayEntry wifi_display[WIFI_DISPLAY_MAX];
static int wifi_display_count = 0;

// Stage-1 (SSID list) widgets — three labels per row: saved icon / SSID / signal.
static lv_obj_t *wifiListRow[WIFI_LIST_VISIBLE]    = { NULL };
static lv_obj_t *wifiListLabel[WIFI_LIST_VISIBLE]  = { NULL };
static lv_obj_t *lblWifiSaved[WIFI_LIST_VISIBLE]   = { NULL };
static lv_obj_t *lblWifiSignal[WIFI_LIST_VISIBLE]  = { NULL };
static lv_obj_t *lblWifiNoResults = NULL;
static lv_obj_t *lblWifiStatus    = NULL;
static lv_obj_t *lblWifiTitle     = NULL;   // doubles as a live status banner

// Connection-attempt state machine. Drives the status banner and decides
// when to bounce the user to the password screen for a retry.
enum WifiConnState { WCS_IDLE, WCS_TRYING, WCS_OK, WCS_FAILED };
static WifiConnState wifi_conn_state           = WCS_IDLE;
static unsigned long wifi_conn_start_ms        = 0;
static unsigned long wifi_conn_state_changed_ms = 0;
static char          wifi_conn_ssid[33]        = "";
#define WIFI_CONN_TIMEOUT_MS 12000UL
#define WIFI_CONN_OK_HOLD_MS  3000UL

// Pass-screen retry banner.
static bool          wifi_retry_due_to_fail    = false;
static lv_obj_t     *lblWifiPassRetry          = NULL;

// Stage-2 (password) screen + widgets.
static lv_obj_t *scrWifiPass         = NULL;
static lv_obj_t *wifiTA_pass         = NULL;
static lv_obj_t *wifiPassKB          = NULL;
static lv_obj_t *lblWifiPassNetwork  = NULL;

// OTA dialog is raised from the UI thread once the boot-time check finds
// a newer version on the server.
static volatile bool ota_prompt_pending = false;
bool execute_ota_update_now = false;
static char  ota_remote_version[24] = "";
static char  ota_download_url[256]  = "";
static lv_obj_t *scrFullGraph     = NULL;

// Fullscreen-graph widgets (mirror of the main chart)
static lv_obj_t *chartFull        = NULL;
static lv_chart_series_t *serTempFull = NULL;
static lv_chart_series_t *serSPFull   = NULL;
#define FULL_X_MAX_LABELS 7
static lv_obj_t *lblFullX[FULL_X_MAX_LABELS] = { NULL };
#define FULL_Y_LABELS 6
static lv_obj_t *lblFullY[FULL_Y_LABELS]     = { NULL };
static lv_obj_t *lblFullTitle     = NULL;

// Index of the saved profile currently being edited in the builder (-1 = new).
static int       builder_editing_idx = -1;
static lv_obj_t *lblBuilderTitle     = NULL;

// Calibration state machine (4 corners, top-left → top-right → bottom-right → bottom-left)
static int      cal_step = 0;          // 0..3 in progress, -1 idle
static int16_t  cal_raw_x[4];
static int16_t  cal_raw_y[4];
static bool     cal_was_touched = false;
static int16_t  cal_last_raw_x = 0, cal_last_raw_y = 0;
static lv_obj_t *calCrosshair = NULL;
static lv_obj_t *lblCalPrompt = NULL;
static lv_timer_t *calTimer   = NULL;
// Target pixel positions for each corner (10 px inset from edges)
static const lv_point_t CAL_TARGETS[4] = {
  { 10, 10 }, { 309, 10 }, { 309, 229 }, { 10, 229 }
};

// Main-screen widgets
static lv_obj_t *arcTemp          = NULL;
static lv_obj_t *lblTempVal       = NULL;
static lv_obj_t *lblSetpoint      = NULL;
static lv_obj_t *lblMode          = NULL;
static lv_obj_t *chartHist        = NULL;
static lv_chart_series_t *serTemp = NULL;
static lv_chart_series_t *serSP   = NULL;
// Up to 4 main-page X-axis labels, dynamically repositioned based on total
// minutes so that visible labels are always multiples of 10.
#define MAIN_X_MAX_LABELS 4
static lv_obj_t *lblXAxis[MAIN_X_MAX_LABELS] = { NULL };
static lv_obj_t *btnProfile       = NULL;
static lv_obj_t *lblBtnProfile    = NULL;
static lv_obj_t *btnStartStop     = NULL;
static lv_obj_t *lblBtnStart      = NULL;
static lv_obj_t *lblGaugeWarn     = NULL;   // blinking ⚠ glyph on the gauge panel
static bool      blink_phase      = false;
static lv_timer_t *blinkTimer     = NULL;

// Engineering-list widgets (paged)
static lv_obj_t *lblEngTitle      = NULL;
static lv_obj_t *btnEngEntry[3];
static lv_obj_t *lblEngEntry[3];
static int       eng_page = 0;
#define ENG_PER_PAGE 3

// Saved custom profiles — persisted in NVS
#define PROFILE_NAME_LEN 32
#define SAVED_CUSTOM_MAX 16
struct SavedCustom {
  char  name[PROFILE_NAME_LEN];
  int   step_count;
  ProfileStep steps[PROFILE_MAX_STEPS];
};
SavedCustom saved_customs[SAVED_CUSTOM_MAX];
int         saved_custom_count = 0;
int         custom_detail_idx  = -1;   // index of profile on scrCustomDetail

// Rename screen widgets
static lv_obj_t *renameTA         = NULL;
static lv_obj_t *renameKB         = NULL;
static lv_obj_t *lblRenameTitle   = NULL;
static int       rename_target_idx   = -1;    // slot being renamed (or -1 for a new save)
static bool      rename_save_builder = false; // true = commit current builder_steps on Save
static char      rename_default_name[PROFILE_NAME_LEN] = "";

// Saved-custom LIST widgets
static lv_obj_t *lblCustomTitle   = NULL;
static lv_obj_t *btnCustomEntry[3];
static lv_obj_t *lblCustomEntry[3];
static int       custom_list_page = 0;

// Builder widgets (editing a new custom profile before saving)
#define BUILDER_PER_PAGE 4
static lv_obj_t *lblBuilderEmpty  = NULL;
static lv_obj_t *btnBuilderEntry[BUILDER_PER_PAGE] = { NULL };
static lv_obj_t *lblBuilderEntry[BUILDER_PER_PAGE] = { NULL };
static lv_obj_t *lblBuilderPage   = NULL;
static int       builder_page = 0;
ProfileStep      builder_steps[PROFILE_MAX_STEPS];
int              builder_step_count = 0;

// -1 = we're ADDING a new step; >=0 = we're EDITING the step at this index.
// Used by the keypad/commit/finalize chain to decide append-vs-overwrite.
static int       editing_step_idx = -1;

// Custom-detail widgets
static lv_obj_t *lblDetailTitle   = NULL;
static lv_obj_t *lblDetailBody    = NULL;

// Add-step / keypad state
enum AddKind { ADD_NONE, ADD_RAMP, ADD_SET };
static AddKind add_kind = ADD_NONE;
static int     add_field_idx = 0;
static float   add_tmp_values[3];

// Keypad
static lv_obj_t *lblKeypadPrompt = NULL;
static lv_obj_t *lblKeypadEntry  = NULL;
static char      keypad_buf[16] = "";

// Currently-selected profile (any source — predef or saved custom)
char  selected_profile_name[PROFILE_NAME_LEN] = "";
bool  profile_is_selected = false;
int   selected_custom_idx = -1;   // -1 unless selected profile is a saved custom

// ══════════════════════════════════════════════════════════════════
//   SECTION 5 — PREDEFINED MATERIAL PROFILES
//   Translated directly from the user's table:
//     RAMP <target C> <rate C/min> <hold min>
//     SET  <target C>            <hold min>
// ══════════════════════════════════════════════════════════════════
struct PredefProfile {
  const char *name;
  int step_count;
  ProfileStep steps[8];
};

// Physical rate caps imposed by the oven hardware. Any predefined profile
// step that would exceed these gets clamped to the cap below; SET steps
// that ask for an instantaneous jump are replaced by a RAMP at the cap.
#define MAX_HEATING_RATE_C_PER_MIN  3.35f
#define MAX_COOLING_RATE_C_PER_MIN  1.89f

// rate_per_sec = C_per_min / 60  ;  hold_sec = hold_min * 60
#define R(tgt, rpm, hm) { true,  (float)(tgt), (float)(rpm)/60.0f, (unsigned long)((hm)*60UL) }

// Every SET has been rewritten as a RAMP at the matching hardware cap.
// Rates up to 3.35 °C/min for heating and 1.89 °C/min for cooling.
static const PredefProfile HOUSEHOLD_PROFILES[] = {
  // PLA  — ambient → 90, hold 2 h, back to 22
  { "PLA",  2, { R( 90, 3.35, 120), R(22, 1.89,   0) } },
  // PETG — ambient → 90, hold 3 h, back to 22
  { "PETG", 2, { R( 90, 3.35, 180), R(22, 1.89,   0) } },
};
static const int HOUSEHOLD_COUNT = sizeof(HOUSEHOLD_PROFILES)/sizeof(HOUSEHOLD_PROFILES[0]);

static const PredefProfile ENGINEERING_PROFILES[] = {
  { "Polypropylene (PP)", 3,
    { R( 60, 2.00,  25), R(110, 2.50, 240), R(22, 0.80,   0) } },
  // PA12 — original recipe asked for 7.0 °C/min; clamped to the heating cap.
  { "Nylon PA12 / PA12-CF", 2,
    { R(150, 3.35, 360), R( 22, 1.00,   0) } },
  { "Nylon PA6-CF / PA6-GF", 3,
    { R( 80, 2.00,  30), R(120, 2.00, 480), R(22, 1.00,   0) } },
  { "Polycarbonate (PC)", 3,
    { R( 60, 2.00,  20), R( 90, 2.00, 120), R(22, 0.65,   0) } },
  { "PET-CF", 3,
    { R( 90, 2.30,  60), R(120, 2.00, 600), R(22, 0.90,   0) } },
  { "PEEK", 3,
    { R(150, 1.00,  60), R(200, 1.00, 120), R(22, 0.167,  0) } },
  { "PPS / PPS-CF", 3,
    { R( 80, 2.00,  60), R(130, 2.00, 180), R(22, 1.00,   0) } },
  // PEI 9085 — middle SET 93 replaced with a cooling ramp at the cap.
  { "PEI / ULTEM 9085", 4,
    { R(121, 3.30,  60), R(149, 2.00,  60), R(93, 1.89,  30), R(22, 0.80, 0) } },
  // PEI 1010 — middle SET 149 replaced with a cooling ramp at the cap.
  { "PEI / ULTEM 1010", 4,
    { R(149, 3.30,  60), R(200, 2.00,  60), R(149, 1.89, 30), R(22, 0.80, 0) } },
  // PAHT-CF — initial SET 80 replaced with a heating ramp at the cap.
  { "PAHT-CF", 2,
    { R( 80, 3.35, 720), R( 22, 1.00,   0) } },
};
static const int ENG_COUNT = sizeof(ENGINEERING_PROFILES)/sizeof(ENGINEERING_PROFILES[0]);

#undef R

// ══════════════════════════════════════════════════════════════════
//   SECTION 6 — HELPERS
// ══════════════════════════════════════════════════════════════════
float getActiveNCR(int bucket) {
  if (bucket < 0) bucket = 0;
  if (bucket >= NCR_LUT_SIZE) bucket = NCR_LUT_SIZE - 1;
  float diff = setpoint - current_temp;
  if (abs(diff) < 1.0f) {
    return (ncr_lin_heat[bucket] + ncr_lin_cool[bucket]) / 2.0f;
  } else if (diff > 0.0f) {
    return ncr_lin_heat[bucket];
  } else {
    return ncr_lin_cool[bucket];
  }
}

float steadyStateIntegral(float sp) {
  if (plant_K <= 0.0f || Kc <= 0.0f || Ti <= 0.0f) return 0.0f;
  int bucket = (int)((sp - 20.0f) / 5.0f);
  if (bucket < 0) bucket = 0;
  if (bucket >= NCR_LUT_SIZE) bucket = NCR_LUT_SIZE - 1;
  float ncr = getActiveNCR(bucket);
  return (ncr / plant_K) * (Ti / Kc);
}

void linearizeNCR(float* raw_saved, float* lin_out, const float* defaults, bool use_poly) {
  float xs[NCR_LUT_SIZE], ys[NCR_LUT_SIZE];
  int n = 0;
  for (int i = 0; i < NCR_LUT_SIZE; i++) {
    if (raw_saved[i] > 0.0f) {
      xs[n] = 20.0f + i * 5.0f;
      ys[n] = raw_saved[i];
      n++;
    }
  }
  if (n < 2) {
    for (int i = 0; i < NCR_LUT_SIZE; i++)
      lin_out[i] = (raw_saved[i] > 0.0f) ? raw_saved[i] : defaults[i];
    return;
  }

  if (use_poly && n >= 3) {
    // 2nd-degree polynomial: y = a*x^2 + b*x + c
    double sx = 0, sy = 0, sx2 = 0, sx3 = 0, sx4 = 0, sxy = 0, sx2y = 0;
    for (int i = 0; i < n; i++) {
      double x = xs[i], y = ys[i];
      sx += x; sy += y;
      sx2 += x*x; sx3 += x*x*x; sx4 += x*x*x*x;
      sxy += x*y; sx2y += x*x*y;
    }
    // Solve 3x3 normal equations via Cramer's rule
    double d0 = (double)n*(sx2*sx4 - sx3*sx3) - sx*(sx*sx4 - sx3*sx2) + sx2*(sx*sx3 - sx2*sx2);
    if (abs(d0) < 1e-20) {
      // Degenerate — fall through to linear
      use_poly = false;
    } else {
      double da = sy*(sx2*sx4 - sx3*sx3) - sx*(sxy*sx4 - sx2y*sx3) + sx2*(sxy*sx3 - sx2y*sx2);
      double db = (double)n*(sxy*sx4 - sx2y*sx3) - sy*(sx*sx4 - sx3*sx2) + sx2*(sx*sx2y - sxy*sx2);
      double dc = (double)n*(sx2*sx2y - sx3*sxy) - sx*(sx*sx2y - sxy*sx2) + sy*(sx*sx3 - sx2*sx2);
      double a = da / d0, b = db / d0, c = dc / d0;
      for (int i = 0; i < NCR_LUT_SIZE; i++) {
        double t = 20.0 + i * 5.0;
        float val = (float)(a + b * t + c * t * t);
        lin_out[i] = max(val, 0.001f);
      }
      return;
    }
  }

  // Linear fit: y = m*x + b
  float sum_x = 0, sum_y = 0, sum_xy = 0, sum_x2 = 0;
  for (int i = 0; i < n; i++) {
    sum_x += xs[i]; sum_y += ys[i];
    sum_xy += xs[i]*ys[i]; sum_x2 += xs[i]*xs[i];
  }
  float denom = n * sum_x2 - sum_x * sum_x;
  if (abs(denom) < 1e-9f) {
    for (int i = 0; i < NCR_LUT_SIZE; i++)
      lin_out[i] = (raw_saved[i] > 0.0f) ? raw_saved[i] : defaults[i];
    return;
  }
  float m = (n * sum_xy - sum_x * sum_y) / denom;
  float b = (sum_y - m * sum_x) / (float)n;
  for (int i = 0; i < NCR_LUT_SIZE; i++) {
    float val = m * (20.0f + i * 5.0f) + b;
    lin_out[i] = max(val, 0.001f);
  }
}

void saveLinearizedLUTs() {
  for (int i = 0; i < NCR_LUT_SIZE; i++) {
    char key[10];
    sprintf(key, "nlh_%d", i);
    preferences.putFloat(key, ncr_lin_heat[i]);
    sprintf(key, "nlc_%d", i);
    preferences.putFloat(key, ncr_lin_cool[i]);
    yield();
  }
}

float getMedian(float array[], int size) {
  float sorted[size];
  for (int i = 0; i < size; i++) sorted[i] = array[i];
  for (int i = 0; i < size - 1; i++) {
    for (int j = 0; j < size - i - 1; j++) {
      if (sorted[j] > sorted[j + 1]) {
        float t = sorted[j];
        sorted[j] = sorted[j + 1];
        sorted[j + 1] = t;
      }
    }
  }
  return sorted[size / 2];
}

// ══════════════════════════════════════════════════════════════════
//   SECTION 7 — ISR  (zero-crossing sigma-delta modulator)
//
//   The PID still produces pid_output ∈ [0,1] at 4 Hz. The main
//   loop converts that into a 16-bit fixed-point increment
//   (sd_increment, Q0.16) that the ISR uses with pure integer
//   math — ESP32 FPU instructions are unsafe in interrupt context
//   (per-task lazy save/restore corrupts on ISR-side FPU use).
//
//   Each full mains cycle we add sd_increment to sd_acc and fire
//   when it overflows 65536. Time-averaged firing density tracks
//   pid_output to 1/65536 ≈ 0.0015 %, far finer than the heater's
//   thermal time constant can resolve.
//
//   The decision is made once per full cycle (every other ZCD edge)
//   so each "on" decision conducts one positive + one negative half
//   — symmetric, no DC offset into transformer-fed loads.
// ══════════════════════════════════════════════════════════════════
volatile uint16_t sd_increment  = 0;
volatile uint32_t sd_acc        = 0;
volatile uint8_t  sd_half_idx   = 0;
volatile bool     sd_fire_cycle = false;

void IRAM_ATTR zcd_isr() {
  if (sd_half_idx == 0) {
    uint16_t inc = sd_increment;
    if (inc == 0) {
      sd_fire_cycle = false;
      sd_acc        = 0;
    } else {
      sd_acc += inc;
      sd_fire_cycle = (sd_acc >= 65536u);
      if (sd_fire_cycle) sd_acc -= 65536u;
    }
  }
  sd_half_idx ^= 1;

  if (sd_fire_cycle) {
    // Wait for line voltage to rise above the triac's latching threshold.
    // Firing exactly at the ZCD edge fails to latch: the optoisolator drops
    // out slightly before the true zero, and immediately after the zero
    // V_load ≈ 0 so I_load < I_L. 230 µs matches the minimum delay the
    // phase-angle firmware used and is well within a half-cycle.
    delayMicroseconds(230);
    digitalWrite(TRIAC_PIN, HIGH);
    delayMicroseconds(150);
    digitalWrite(TRIAC_PIN, LOW);
  }
}

// ══════════════════════════════════════════════════════════════════
//   SECTION 8 — MAX6675 via HARDWARE VSPI (transactional)
//   Replaces the old bit-banged MAX6675 library so that the same
//   VSPI bus can be shared with TFT_eSPI and XPT2046.
// ══════════════════════════════════════════════════════════════════
float readMAX6675() {
  SPI.beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE0));
  digitalWrite(CS_PIN, LOW);
  delayMicroseconds(1);
  uint16_t raw = SPI.transfer16(0x0000);
  digitalWrite(CS_PIN, HIGH);
  SPI.endTransaction();
  if (raw & 0x04) return NAN;
  return (raw >> 3) * 0.25f;
}

// Forward declarations
void ui_init(void);
void ui_update(void);
void ui_show_messagebox(const char *title, const char *body,
                        const char *btn_ok, const char *btn_cancel,
                        lv_event_cb_t ok_cb);
void ui_show_alert(const char *title, const char *body);
void ui_show_info (const char *title, const char *body);
void ui_show_about(void);
void show_scrMain(void);
void show_scrMaterial(void);
void show_scrHousehold(void);
void show_scrEngineer(void);
void show_scrCustom(void);
void show_scrCustomDetail(int idx);
void show_scrBuilder(void);
void show_scrAddType(void);
void show_scrKeypad(const char *prompt);
void show_scrSettings(void);
void show_scrCalibrate(void);
void show_scrRename(void);
static void generate_next_custom_name(char *out, size_t out_size);
void show_scrFullGraph(void);
void refresh_profile_preview(void);
void cal_begin(void);
void cal_finish_and_save(void);
void cal_draw_target(int idx);
static void cal_timer_cb(lv_timer_t *t);
void refresh_eng_page(void);
void refresh_custom_list(void);
void refresh_builder_page(void);
void commit_keypad_value(void);
void finalize_add_step(void);
void my_disp_flush(lv_disp_drv_t *, const lv_area_t *, lv_color_t *);
void my_touchpad_read(lv_indev_drv_t *, lv_indev_data_t *);

// Custom-profile persistence
void loadCustomProfiles(void);

// WiFi + OTA
void loadSavedNets(void);
void saveSavedNets(void);
void wifiConnectAsync(void);
void wifiDisconnect(void);
void checkForUpdate(void);
void performUpdate(void);
void show_scrWifi(void);
void show_scrWifiPass(void);
void show_scrOTA (void);
void wifiStartScan(void);
void wifiPollScan(void);
void wifiAttemptConnect(const char *ssid, const char *pass);
void refreshWifiList(void);
void saveCustomProfiles(void);
bool addSavedCustom(const ProfileStep *steps, int count);
void deleteSavedCustom(int idx);

// Graph / planned-trajectory
void computePlannedTrajectory(const ProfileStep *steps, int count, float start_temp);
void setupProfileGraph(void);
void teardownProfileGraph(void);
void updateProfileGraphActual(void);

// ══════════════════════════════════════════════════════════════════
//   SECTION 8B — CUSTOM PROFILE PERSISTENCE (NVS namespace "custom")
// ══════════════════════════════════════════════════════════════════
#define CUSTOM_MAGIC 0x42

void loadCustomProfiles() {
  Preferences p;
  p.begin("custom", true);
  uint8_t magic = p.getUChar("magic", 0);
  if (magic != CUSTOM_MAGIC) { saved_custom_count = 0; p.end(); return; }
  int n = p.getInt("count", 0);
  if (n < 0) n = 0;
  if (n > SAVED_CUSTOM_MAX) n = SAVED_CUSTOM_MAX;
  saved_custom_count = n;
  for (int i = 0; i < n; i++) {
    char k[12];
    snprintf(k, sizeof(k), "n_%d", i);
    p.getString(k, saved_customs[i].name, PROFILE_NAME_LEN);
    snprintf(k, sizeof(k), "c_%d", i);
    saved_customs[i].step_count = p.getInt(k, 0);
    if (saved_customs[i].step_count < 0 ||
        saved_customs[i].step_count > PROFILE_MAX_STEPS) {
      saved_customs[i].step_count = 0;
    }
    snprintf(k, sizeof(k), "d_%d", i);
    size_t need = saved_customs[i].step_count * sizeof(ProfileStep);
    if (need > 0) p.getBytes(k, saved_customs[i].steps, need);
  }
  p.end();
}

void saveCustomProfiles() {
  Preferences p;
  p.begin("custom", false);
  p.clear();
  p.putUChar("magic", CUSTOM_MAGIC);
  p.putInt("count", saved_custom_count);
  for (int i = 0; i < saved_custom_count; i++) {
    char k[12];
    snprintf(k, sizeof(k), "n_%d", i);
    p.putString(k, saved_customs[i].name);
    snprintf(k, sizeof(k), "c_%d", i);
    p.putInt(k, saved_customs[i].step_count);
    snprintf(k, sizeof(k), "d_%d", i);
    p.putBytes(k, saved_customs[i].steps,
               saved_customs[i].step_count * sizeof(ProfileStep));
  }
  p.end();
}

bool addSavedCustom(const ProfileStep *steps, int count) {
  if (count <= 0 || count > PROFILE_MAX_STEPS) return false;
  if (saved_custom_count >= SAVED_CUSTOM_MAX)  return false;
  int slot = saved_custom_count;
  // Auto-name: "Custom Profile N" where N = smallest unused sequential number
  int used_max = 0;
  for (int i = 0; i < saved_custom_count; i++) {
    int n = 0;
    if (sscanf(saved_customs[i].name, "Custom Profile %d", &n) == 1) {
      if (n > used_max) used_max = n;
    }
  }
  snprintf(saved_customs[slot].name, PROFILE_NAME_LEN,
           "Custom Profile %d", used_max + 1);
  saved_customs[slot].step_count = count;
  for (int i = 0; i < count; i++) saved_customs[slot].steps[i] = steps[i];
  saved_custom_count++;
  saveCustomProfiles();
  return true;
}

void deleteSavedCustom(int idx) {
  if (idx < 0 || idx >= saved_custom_count) return;
  for (int i = idx; i < saved_custom_count - 1; i++) {
    saved_customs[i] = saved_customs[i + 1];
  }
  saved_custom_count--;
  saveCustomProfiles();
}

// ══════════════════════════════════════════════════════════════════
//   SECTION 8BB — WIFI CREDENTIALS + CONNECT
// ══════════════════════════════════════════════════════════════════
// Saved-networks NVS layout (namespace "wifi"):
//   "count"  (int)              — number of saved entries
//   "n_<i>"  (string)           — SSID for slot i
//   "p_<i>"  (string)           — password for slot i
// Legacy single-network layout (old "ssid"/"pass" strings) is auto-imported
// into slot 0 on first boot after the upgrade.

void saveSavedNets() {
  Preferences p;
  p.begin("wifi", false);
  p.clear();   // we own this namespace; rewrite the whole list
  p.putInt("count", saved_net_count);
  for (int i = 0; i < saved_net_count; i++) {
    char k[8];
    snprintf(k, sizeof(k), "n_%d", i);
    p.putString(k, saved_nets[i].ssid);
    snprintf(k, sizeof(k), "p_%d", i);
    p.putString(k, saved_nets[i].pass);
  }
  p.end();
}

void loadSavedNets() {
  saved_net_count = 0;
  Preferences p;
  p.begin("wifi", true);
  bool has_count = p.isKey("count");
  if (has_count) {
    int n = p.getInt("count", 0);
    if (n < 0) n = 0;
    if (n > SAVED_NET_MAX) n = SAVED_NET_MAX;
    saved_net_count = n;
    for (int i = 0; i < n; i++) {
      char k[8];
      snprintf(k, sizeof(k), "n_%d", i);
      p.getString(k, saved_nets[i].ssid, sizeof(saved_nets[i].ssid));
      snprintf(k, sizeof(k), "p_%d", i);
      p.getString(k, saved_nets[i].pass, sizeof(saved_nets[i].pass));
    }
    p.end();
  } else {
    // Migrate from the legacy single ssid/pass keys.
    char old_ssid[33] = "";
    char old_pass[65] = "";
    p.getString("ssid", old_ssid, sizeof(old_ssid));
    p.getString("pass", old_pass, sizeof(old_pass));
    p.end();
    if (old_ssid[0]) {
      strncpy(saved_nets[0].ssid, old_ssid, sizeof(saved_nets[0].ssid) - 1);
      saved_nets[0].ssid[sizeof(saved_nets[0].ssid) - 1] = 0;
      strncpy(saved_nets[0].pass, old_pass, sizeof(saved_nets[0].pass) - 1);
      saved_nets[0].pass[sizeof(saved_nets[0].pass) - 1] = 0;
      saved_net_count = 1;
      saveSavedNets();   // rewrite to the new layout
    }
  }
  // Mirror the first slot into the active wifi_ssid/wifi_pass so the
  // existing auto-reconnect path Just Works.
  if (saved_net_count > 0) {
    strncpy(wifi_ssid, saved_nets[0].ssid, sizeof(wifi_ssid) - 1);
    wifi_ssid[sizeof(wifi_ssid) - 1] = 0;
    strncpy(wifi_pass, saved_nets[0].pass, sizeof(wifi_pass) - 1);
    wifi_pass[sizeof(wifi_pass) - 1] = 0;
  } else {
    wifi_ssid[0] = 0;
    wifi_pass[0] = 0;
  }
}

static int findSavedByName(const char *ssid) {
  if (!ssid) return -1;
  for (int i = 0; i < saved_net_count; i++) {
    if (strcmp(saved_nets[i].ssid, ssid) == 0) return i;
  }
  return -1;
}

// Insert or update by SSID. If full, drops the oldest (slot 0) and shifts.
// Returns the slot index of the resulting entry.
static int addOrUpdateSavedNet(const char *ssid, const char *pass) {
  if (!ssid || !ssid[0]) return -1;
  int idx = findSavedByName(ssid);
  if (idx >= 0) {
    strncpy(saved_nets[idx].pass, pass ? pass : "", sizeof(saved_nets[idx].pass) - 1);
    saved_nets[idx].pass[sizeof(saved_nets[idx].pass) - 1] = 0;
    saveSavedNets();
    return idx;
  }
  if (saved_net_count >= SAVED_NET_MAX) {
    // Drop the oldest (slot 0); shift the rest down.
    for (int i = 0; i < SAVED_NET_MAX - 1; i++) saved_nets[i] = saved_nets[i + 1];
    saved_net_count = SAVED_NET_MAX - 1;
  }
  int slot = saved_net_count++;
  strncpy(saved_nets[slot].ssid, ssid, sizeof(saved_nets[slot].ssid) - 1);
  saved_nets[slot].ssid[sizeof(saved_nets[slot].ssid) - 1] = 0;
  strncpy(saved_nets[slot].pass, pass ? pass : "", sizeof(saved_nets[slot].pass) - 1);
  saved_nets[slot].pass[sizeof(saved_nets[slot].pass) - 1] = 0;
  saveSavedNets();
  return slot;
}

// Kick off an asynchronous connect (non-blocking). Poll WiFi.status() at
// leisure — we don't stall the control loop here.
void wifiConnectAsync() {
  if (!wifi_ssid[0]) return;
  WiFi.mode(WIFI_STA);
  WiFi.begin(wifi_ssid, wifi_pass);
  Serial.print("[WIFI] Connecting to SSID: ");
  Serial.println(wifi_ssid);
}

void wifiDisconnect() {
  WiFi.disconnect(true);
  WiFi.mode(WIFI_OFF);
  wifi_connected_flag = false;
}

// Kick a connection attempt and arm the state machine. Used by both the
// "tap a saved network" path and the "save password" path. Call from the
// UI thread.
void wifiAttemptConnect(const char *ssid, const char *pass) {
  if (!ssid || !ssid[0]) return;
  strncpy(wifi_conn_ssid, ssid, sizeof(wifi_conn_ssid) - 1);
  wifi_conn_ssid[sizeof(wifi_conn_ssid) - 1] = 0;
  wifi_conn_state            = WCS_TRYING;
  wifi_conn_start_ms         = millis();
  wifi_conn_state_changed_ms = millis();
  WiFi.disconnect(false);     // soft drop; keeps NVS config
  delay(50);                  // let the RTOS push the disconnect event
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, pass ? pass : "");
  Serial.print("[WIFI] Attempting connect to ");
  Serial.println(ssid);
  refreshWifiList();
}

// Kick off a non-blocking network scan. Results are harvested in
// wifiPollScan() which is polled from the main loop.
void wifiStartScan() {
  WiFi.mode(WIFI_STA);
  WiFi.scanDelete();              // drop any previous result buffer
  WiFi.scanNetworks(true, false); // async, no hidden APs
  wifi_scan_in_progress = true;
  wifi_scan_count       = 0;
  wifi_sel_idx          = 0;
  wifi_list_top         = 0;
  Serial.println("[WIFI] Scan started.");
}

void wifiPollScan() {
  if (!wifi_scan_in_progress) return;
  int n = WiFi.scanComplete();
  if (n == WIFI_SCAN_RUNNING) return;     // still working
  wifi_scan_in_progress = false;
  if (n < 0) {
    Serial.print("[WIFI] Scan failed: "); Serial.println(n);
    refreshWifiList();
    return;
  }
  if (n > WIFI_SCAN_MAX) n = WIFI_SCAN_MAX;
  wifi_scan_count = n;
  for (int i = 0; i < n; i++) {
    String s = WiFi.SSID(i);
    strncpy(wifi_scan_results[i].ssid, s.c_str(), 32);
    wifi_scan_results[i].ssid[32] = 0;
    wifi_scan_results[i].rssi     = (int8_t)WiFi.RSSI(i);
    wifi_scan_results[i].enc      = (uint8_t)WiFi.encryptionType(i);
  }
  WiFi.scanDelete();
  // Pre-select the currently saved SSID if it's in the list.
  for (int i = 0; i < n; i++) {
    if (wifi_ssid[0] && strcmp(wifi_scan_results[i].ssid, wifi_ssid) == 0) {
      wifi_sel_idx  = i;
      if (wifi_sel_idx >= WIFI_LIST_VISIBLE)
        wifi_list_top = wifi_sel_idx - WIFI_LIST_VISIBLE + 1;
      break;
    }
  }
  Serial.print("[WIFI] Scan done, "); Serial.print(n); Serial.println(" networks.");
  refreshWifiList();
}

// Repaint the list rows from wifi_scan_results based on wifi_list_top
// and the highlight row (wifi_sel_idx).
// Stitch saved networks (pinned at the top) and freshly-scanned networks
// (deduped against saved entries) into wifi_display[].
static void rebuildWifiDisplay() {
  wifi_display_count = 0;

  // Saved entries first — always shown, in_range marked from scan results.
  for (int i = 0; i < saved_net_count && wifi_display_count < WIFI_DISPLAY_MAX; i++) {
    WifiDisplayEntry &d = wifi_display[wifi_display_count++];
    d.ssid     = saved_nets[i].ssid;
    d.is_saved = true;
    d.in_range = false;
    d.rssi     = -127;
    for (int j = 0; j < wifi_scan_count; j++) {
      if (strcmp(saved_nets[i].ssid, wifi_scan_results[j].ssid) == 0) {
        d.in_range = true;
        d.rssi     = wifi_scan_results[j].rssi;
        break;
      }
    }
  }

  // Then scan-only entries (not already in the saved list).
  for (int j = 0; j < wifi_scan_count && wifi_display_count < WIFI_DISPLAY_MAX; j++) {
    bool already_listed = false;
    for (int i = 0; i < saved_net_count; i++) {
      if (strcmp(wifi_scan_results[j].ssid, saved_nets[i].ssid) == 0) {
        already_listed = true; break;
      }
    }
    if (already_listed) continue;
    WifiDisplayEntry &d = wifi_display[wifi_display_count++];
    d.ssid     = wifi_scan_results[j].ssid;
    d.is_saved = false;
    d.in_range = true;
    d.rssi     = wifi_scan_results[j].rssi;
  }

  // Clamp cursor / scroll-top to valid range.
  if (wifi_sel_idx  >= wifi_display_count) wifi_sel_idx  = wifi_display_count > 0 ? wifi_display_count - 1 : 0;
  if (wifi_list_top >  wifi_sel_idx)        wifi_list_top = wifi_sel_idx;
  if (wifi_list_top + WIFI_LIST_VISIBLE <= wifi_sel_idx)
    wifi_list_top = wifi_sel_idx - WIFI_LIST_VISIBLE + 1;
  if (wifi_list_top < 0) wifi_list_top = 0;
}

void refreshWifiList() {
  rebuildWifiDisplay();

  // ---- Title / status banner ---------------------------------------------
  if (lblWifiTitle) {
    char buf[64];
    uint32_t color = CLR_TXT;
    const char *txt = "WiFi Networks";
    if (wifi_conn_state == WCS_TRYING) {
      txt   = "Connecting...";
      color = CLR_AMBER;
    } else if (wifi_conn_state == WCS_OK) {
      txt   = "Connected";
      color = CLR_SUCCESS;
    } else if (wifi_conn_state == WCS_FAILED) {
      txt   = "Connection failed";
      color = CLR_DANGER;
    } else if (wifi_scan_in_progress) {
      txt   = "Scanning...";
      color = CLR_TXT_DIM;
    }
    lv_label_set_text(lblWifiTitle, txt);
    lv_obj_set_style_text_color(lblWifiTitle, lv_color_hex(color), 0);
  }

  // SSID currently associated, used to paint that row green.
  String connected = (WiFi.status() == WL_CONNECTED) ? WiFi.SSID() : String("");

  if (wifi_display_count == 0) {
    if (lblWifiNoResults) {
      // Show "Scanning..." whenever we're either actively scanning OR no
      // scan has ever finished yet — i.e. the user has just landed on the
      // screen. Only flip to "No networks" once a scan has completed and
      // produced nothing.
      bool ever_scanned = !wifi_scan_in_progress && wifi_scan_count == 0
                          && saved_net_count == 0;
      lv_label_set_text(lblWifiNoResults,
        wifi_scan_in_progress ? "Scanning..."
                              : (ever_scanned ? "Scanning..." : "No networks"));
      lv_obj_clear_flag(lblWifiNoResults, LV_OBJ_FLAG_HIDDEN);
    }
    for (int i = 0; i < WIFI_LIST_VISIBLE; i++)
      if (wifiListRow[i]) lv_obj_add_flag(wifiListRow[i], LV_OBJ_FLAG_HIDDEN);
    return;
  }
  if (lblWifiNoResults) lv_obj_add_flag(lblWifiNoResults, LV_OBJ_FLAG_HIDDEN);

  for (int i = 0; i < WIFI_LIST_VISIBLE; i++) {
    int idx = wifi_list_top + i;
    if (idx >= wifi_display_count) {
      lv_obj_add_flag(wifiListRow[i], LV_OBJ_FLAG_HIDDEN);
      continue;
    }
    const WifiDisplayEntry &e = wifi_display[idx];
    bool selected   = (idx == wifi_sel_idx);
    bool is_active  = (connected.length() > 0) && (connected == e.ssid);

    // Saved icon (left): checkmark in amber, brightened to green if connected.
    if (lblWifiSaved[i]) {
      if (e.is_saved) {
        lv_label_set_text(lblWifiSaved[i], LV_SYMBOL_OK);
        lv_obj_set_style_text_color(lblWifiSaved[i],
          lv_color_hex(is_active ? CLR_SUCCESS : CLR_AMBER), 0);
        lv_obj_clear_flag(lblWifiSaved[i], LV_OBJ_FLAG_HIDDEN);
      } else {
        lv_obj_add_flag(lblWifiSaved[i], LV_OBJ_FLAG_HIDDEN);
      }
    }

    // SSID label
    lv_label_set_text(wifiListLabel[i], e.ssid);
    uint32_t ssid_color;
    if (is_active)      ssid_color = CLR_SUCCESS;
    else if (selected)  ssid_color = CLR_TXT;
    else                ssid_color = CLR_TXT_DIM;
    lv_obj_set_style_text_color(wifiListLabel[i], lv_color_hex(ssid_color), 0);

    // Signal indicator (right): WiFi glyph color-tiered by RSSI, or X if
    // a saved network isn't currently visible.
    if (lblWifiSignal[i]) {
      uint32_t sig_color;
      const char *sig_glyph;
      if (!e.in_range) {
        sig_glyph = LV_SYMBOL_CLOSE;
        sig_color = CLR_TXT_FAINT;
      } else {
        sig_glyph = LV_SYMBOL_WIFI;
        if      (e.rssi >= -60) sig_color = CLR_SUCCESS;
        else if (e.rssi >= -75) sig_color = CLR_AMBER;
        else                    sig_color = CLR_DANGER;
        if (is_active) sig_color = CLR_SUCCESS;
      }
      lv_label_set_text(lblWifiSignal[i], sig_glyph);
      lv_obj_set_style_text_color(lblWifiSignal[i], lv_color_hex(sig_color), 0);
    }

    // Row background
    lv_obj_set_style_bg_color(wifiListRow[i],
      lv_color_hex(selected ? CLR_ACCENT_D : CLR_PANEL2), 0);

    lv_obj_clear_flag(wifiListRow[i], LV_OBJ_FLAG_HIDDEN);
  }
}

// ══════════════════════════════════════════════════════════════════
//   SECTION 8CC — OTA UPDATE CHECK
//   Fetches OTA_MANIFEST_URL, parses the tiny JSON, and if the server
//   version differs from FIRMWARE_VERSION raises the UI prompt flag.
// ══════════════════════════════════════════════════════════════════
// Minimal string extractor for `"key":"value"` — avoids pulling in a full
// JSON library just for two fields. NOT robust against escaped quotes or
// whitespace edge cases — keep the manifest JSON well-behaved on the server.
static bool json_extract(const String &body, const char *key, char *out, size_t out_sz) {
  String needle = String("\"") + key + "\"";
  int k = body.indexOf(needle);
  if (k < 0) return false;
  int q1 = body.indexOf('"', k + needle.length());
  if (q1 < 0) return false;
  q1 = body.indexOf('"', q1);
  if (q1 < 0) return false;
  int q2 = body.indexOf('"', q1 + 1);
  if (q2 < 0) return false;
  String val = body.substring(q1 + 1, q2);
  strncpy(out, val.c_str(), out_sz - 1);
  out[out_sz - 1] = 0;
  return true;
}

void checkForUpdate() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[OTA] No WiFi — skipping update check.");
    return;
  }
  WiFiClientSecure secureClient;
  secureClient.setCACertBundle(x509_crt_bundle, x509_crt_bundle_len);  // verifies any common CA

  HTTPClient http;
  http.setTimeout(8000);
  
  if (!http.begin(secureClient, OTA_MANIFEST_URL)) {
    Serial.println("[OTA] http.begin() failed.");
    return;
  }

  int code = http.GET();
  if (code != HTTP_CODE_OK) {
    Serial.print("[OTA] Manifest fetch failed, HTTP ");
    Serial.println(code);
    http.end();
    return;
  }
  String body = http.getString();
  http.end();

  char ver[24] = "", url[256] = "";
  if (!json_extract(body, "version", ver, sizeof(ver)) ||
      !json_extract(body, "url",     url, sizeof(url))) {
    Serial.println("[OTA] Malformed manifest.");
    return;
  }
  Serial.print("[OTA] Remote version: "); Serial.println(ver);
  Serial.print("[OTA] Local  version: "); Serial.println(FIRMWARE_VERSION);
  if (strcmp(ver, FIRMWARE_VERSION) == 0) {
    Serial.println("[OTA] Already up to date.");
    return;
  }
  strncpy(ota_remote_version, ver, sizeof(ota_remote_version) - 1);
  strncpy(ota_download_url,   url, sizeof(ota_download_url) - 1);
  ota_prompt_pending = true;
}

// Blocking: downloads firmware.bin over HTTPS and writes it to the inactive
// OTA partition, then reboots. The OTA progress screen is shown for the
// duration; the onProgress callback updates the bar and pumps LVGL on
// every chunk so the screen never appears frozen.
void performUpdate() {
  if (WiFi.status() != WL_CONNECTED) {
    ui_show_alert("Offline", "WiFi is not connected.");
    return;
  }
  if (!ota_download_url[0]) {
    ui_show_alert("No URL", "Update URL missing.");
    return;
  }
  // Refuse mid-process: a profile / tune / learn must be stopped first.
  if (profile_state > 0 || tune_state > 0 || learn_state > 0) {
    ui_show_alert("Busy",
                  "Stop the running profile / tune / learn before updating.");
    return;
  }

  // Safety: the OTA download blocks the main loop, so the 250 ms tick
  // that normally syncs sd_increment from pid_output may not run again
  // until after the flash write. Force the modulator off directly.
  pid_output       = 0.0f;
  sd_increment     = 0;
  setpoint         = 20.0f;
  current_setpoint = current_temp;
  is_ramping       = false;

  // Show the OTA progress screen and pump once so it actually paints
  // before the blocking download starts.
  show_scrOTA();
  for(int i=0; i<5; i++) {
      lv_tick_inc(10);
      lv_task_handler();
      delay(10);
  }


  Serial.print("[OTA] Downloading: "); Serial.println(ota_download_url);
  WiFiClientSecure secureClient;
  secureClient.setCACertBundle(x509_crt_bundle, x509_crt_bundle_len);  // verifies any common CA

  // Progress: called on every chunk by HTTPUpdate. We update the bar +
  // status label and call lv_task_handler() so LVGL can flush the change
  // before HTTPUpdate goes back to blocking on the next chunk.
  httpUpdate.onProgress([](int cur, int total) {
    if (total <= 0 || !barOTA || !lblOTAStatus) return;
    int pct = (int)((100L * (long)cur) / (long)total);
    if (pct < 0)   pct = 0;
    if (pct > 100) pct = 100;
    lv_bar_set_value(barOTA, pct, LV_ANIM_OFF);
    char buf[48];
    snprintf(buf, sizeof(buf), "Downloading...  %d%%", pct);
    lv_label_set_text(lblOTAStatus, buf);
    lv_tick_inc(50);
    lv_task_handler();
  });
  httpUpdate.onError([](int err) {
    Serial.printf("[OTA] httpUpdate error %d\n", err);
  });

  // Reboot ourselves so the user sees the "Complete!" frame first.
  httpUpdate.rebootOnUpdate(false);
  t_httpUpdate_return ret = httpUpdate.update(secureClient, ota_download_url);

  if (ret == HTTP_UPDATE_OK) {
    Serial.println("[OTA] Update OK — rebooting in 1.5 s.");
    if (barOTA)       lv_bar_set_value(barOTA, 100, LV_ANIM_OFF);
    if (lblOTAStatus) lv_label_set_text(lblOTAStatus, "Complete!  Rebooting...");
    lv_task_handler();
    delay(1500);
    ESP.restart();   // never returns
  } else {
    const char *err_str = httpUpdate.getLastErrorString().c_str();
    Serial.printf("[OTA] FAILED: (%d) %s\n",
                  httpUpdate.getLastError(), err_str);
    if (lblOTAStatus) {
      char buf[96];
      snprintf(buf, sizeof(buf), "Failed: %s",
               (err_str && *err_str) ? err_str : "unknown error");
      lv_label_set_text(lblOTAStatus, buf);
    }
    lv_task_handler();
    delay(3500);
    show_scrMain();
  }
}

// ══════════════════════════════════════════════════════════════════
//   SECTION 8C — PLANNED TRAJECTORY + GRAPH STATE MACHINE
// ══════════════════════════════════════════════════════════════════
void computePlannedTrajectory(const ProfileStep *steps, int count, float start_temp) {
  // Build a list of linear segments (start_time, end_time, start_temp, end_temp)
  struct Seg { float t0, t1, T0, T1; };
  Seg segs[PROFILE_MAX_STEPS * 2 + 1];
  int nseg = 0;
  float cur_t = 0.0f;
  float cur_T = start_temp;

  for (int i = 0; i < count; i++) {
    if (steps[i].is_ramp) {
      float dt = (steps[i].rate_per_sec > 1e-6f)
                   ? fabsf(steps[i].target - cur_T) / steps[i].rate_per_sec
                   : 0.0f;
      segs[nseg].t0 = cur_t; segs[nseg].t1 = cur_t + dt;
      segs[nseg].T0 = cur_T; segs[nseg].T1 = steps[i].target;
      nseg++;
      cur_t += dt;
      cur_T  = steps[i].target;
    } else {
      // SET: instantaneous setpoint jump — draw it as a zero-width segment.
      segs[nseg].t0 = cur_t; segs[nseg].t1 = cur_t;
      segs[nseg].T0 = cur_T; segs[nseg].T1 = steps[i].target;
      nseg++;
      cur_T = steps[i].target;
    }
    if (steps[i].hold_sec > 0) {
      float hs = (float)steps[i].hold_sec;
      segs[nseg].t0 = cur_t; segs[nseg].t1 = cur_t + hs;
      segs[nseg].T0 = cur_T; segs[nseg].T1 = cur_T;
      nseg++;
      cur_t += hs;
    }
  }

  profile_total_duration_s = (cur_t > 1.0f) ? cur_t : 1.0f;

  for (int p = 0; p < GRAPH_SAMPLES; p++) {
    float t = (profile_total_duration_s * (float)p) / (float)(GRAPH_SAMPLES - 1);
    float val = start_temp;
    for (int s = 0; s < nseg; s++) {
      if (t <= segs[s].t1 + 0.001f) {
        if (segs[s].t1 > segs[s].t0) {
          float frac = (t - segs[s].t0) / (segs[s].t1 - segs[s].t0);
          if (frac < 0.0f) frac = 0.0f;
          if (frac > 1.0f) frac = 1.0f;
          val = segs[s].T0 + frac * (segs[s].T1 - segs[s].T0);
        } else {
          val = segs[s].T1;
        }
        break;
      }
    }
    profile_planned[p] = val;
  }
  profile_has_plan = true;
  profile_last_slot_filled = -1;
}

// Pick a "nice" tick step in whole minutes: the smallest multiple of 10 that
// yields ≤ max_ticks tick positions across the total duration. Returns a
// step in minutes (minimum 10). For very short totals (<10 min) we relax to
// a step of 10 and simply place one tick at 0.
static int pick_tick_step_minutes(float total_min, int max_ticks) {
  if (total_min < 10.0f) return 10;
  static const int CANDIDATES[] = { 10, 20, 30, 60, 120, 300, 600 };
  for (unsigned i = 0; i < sizeof(CANDIDATES) / sizeof(CANDIDATES[0]); i++) {
    int step = CANDIDATES[i];
    if ((int)ceilf(total_min / (float)step) + 1 <= max_ticks) return step;
  }
  return CANDIDATES[sizeof(CANDIDATES) / sizeof(CANDIDATES[0]) - 1];
}

// Position a label's horizontal anchor such that its CENTER is at plot_left+px_offset.
static void place_xlabel(lv_obj_t *lbl, int plot_left, int px_offset, int y) {
  // Let LVGL compute self_width, then shift by half.
  lv_obj_update_layout(lbl);
  int w = lv_obj_get_width(lbl);
  int x = plot_left + px_offset - w / 2;
  if (x < 0) x = 0;
  lv_obj_set_pos(lbl, x, y);
}

// ---- MAIN PAGE (graphPanel-relative coords) ----
// chart at (3,3) in panel, pad_left=26 → plot_left = 3+26 = 29.
// chart width 150, right edge inside panel = 3+150 = 153; plot_right = 153.
// plot draw width = 124. Labels y=112.
// Plot draw area is the chart widget (at panel x=3..153) minus its 4-px
// horizontal padding on either side → x=7..149 in panel coords.
#define MAIN_PLOT_LEFT     7
#define MAIN_PLOT_RIGHT  149
#define MAIN_PLOT_WIDTH  (MAIN_PLOT_RIGHT - MAIN_PLOT_LEFT)
#define MAIN_XLABEL_Y    112

static void set_main_xaxis_profile(float total_s) {
  float total_min = total_s / 60.0f;
  if (total_min < 0.1f) total_min = 0.1f;
  int step = pick_tick_step_minutes(total_min, MAIN_X_MAX_LABELS);
  int shown = 0;
  for (int t = 0; t <= (int)floorf(total_min + 0.5f) && shown < MAIN_X_MAX_LABELS;
       t += step) {
    int px = (int)roundf((float)t / total_min * (float)MAIN_PLOT_WIDTH);
    if (px < 0) px = 0;
    if (px > MAIN_PLOT_WIDTH) px = MAIN_PLOT_WIDTH;
    char buf[16];
    snprintf(buf, sizeof(buf), (shown == 0 ? "%d" : "%d"), t);
    lv_label_set_text(lblXAxis[shown], buf);
    lv_obj_clear_flag(lblXAxis[shown], LV_OBJ_FLAG_HIDDEN);
    place_xlabel(lblXAxis[shown], MAIN_PLOT_LEFT, px, MAIN_XLABEL_Y);
    shown++;
    if (step <= 0) break;
  }
  for (int i = shown; i < MAIN_X_MAX_LABELS; i++)
    lv_obj_add_flag(lblXAxis[i], LV_OBJ_FLAG_HIDDEN);
}

static void set_main_xaxis_idle() {
  // 60 min rolling window. Fixed step=20 → labels 60, 40, 20, 0 (4 labels)
  // rendering right-to-left across the plot area (newest is right edge).
  const int step = 20;
  int vals[MAIN_X_MAX_LABELS] = { 60, 40, 20, 0 };
  for (int i = 0; i < MAIN_X_MAX_LABELS; i++) {
    int t_ago = vals[i];                            // minutes ago
    int px = (int)roundf((60 - t_ago) / 60.0f * (float)MAIN_PLOT_WIDTH);
    char buf[8];
    snprintf(buf, sizeof(buf), "%d", t_ago);
    lv_label_set_text(lblXAxis[i], buf);
    lv_obj_clear_flag(lblXAxis[i], LV_OBJ_FLAG_HIDDEN);
    place_xlabel(lblXAxis[i], MAIN_PLOT_LEFT, px, MAIN_XLABEL_Y);
  }
  (void)step;
}

// ---- FULLSCREEN (scrFullGraph-absolute coords) ----
// chart spans x=5..315 with pad_left=4 → plot_left = 5+4 = 9; plot_right = 315.
// See build_scrFullGraph below. Labels y=208.
#define FULL_PLOT_LEFT    9
#define FULL_PLOT_RIGHT 315
#define FULL_PLOT_WIDTH  (FULL_PLOT_RIGHT - FULL_PLOT_LEFT)
#define FULL_XLABEL_Y   208

static void set_full_xaxis_profile(float total_s) {
  float total_min = total_s / 60.0f;
  if (total_min < 0.1f) total_min = 0.1f;
  int step = pick_tick_step_minutes(total_min, FULL_X_MAX_LABELS);
  int shown = 0;
  for (int t = 0; t <= (int)floorf(total_min + 0.5f) && shown < FULL_X_MAX_LABELS;
       t += step) {
    int px = (int)roundf((float)t / total_min * (float)FULL_PLOT_WIDTH);
    if (px < 0) px = 0;
    if (px > FULL_PLOT_WIDTH) px = FULL_PLOT_WIDTH;
    char buf[16];
    snprintf(buf, sizeof(buf), "%d", t);
    lv_label_set_text(lblFullX[shown], buf);
    lv_obj_clear_flag(lblFullX[shown], LV_OBJ_FLAG_HIDDEN);
    place_xlabel(lblFullX[shown], FULL_PLOT_LEFT, px, FULL_XLABEL_Y);
    shown++;
    if (step <= 0) break;
  }
  for (int i = shown; i < FULL_X_MAX_LABELS; i++)
    lv_obj_add_flag(lblFullX[i], LV_OBJ_FLAG_HIDDEN);
  if (lblFullTitle) lv_label_set_text(lblFullTitle, "Profile trace");
}

static void set_full_xaxis_idle() {
  // 60 min history. Step 10 → labels at 60, 50, 40, 30, 20, 10, 0 (7 labels)
  int vals[FULL_X_MAX_LABELS] = { 60, 50, 40, 30, 20, 10, 0 };
  for (int i = 0; i < FULL_X_MAX_LABELS; i++) {
    int t_ago = vals[i];
    int px = (int)roundf((60 - t_ago) / 60.0f * (float)FULL_PLOT_WIDTH);
    char buf[8];
    snprintf(buf, sizeof(buf), "%d", t_ago);
    lv_label_set_text(lblFullX[i], buf);
    lv_obj_clear_flag(lblFullX[i], LV_OBJ_FLAG_HIDDEN);
    place_xlabel(lblFullX[i], FULL_PLOT_LEFT, px, FULL_XLABEL_Y);
  }
  if (lblFullTitle) lv_label_set_text(lblFullTitle, "60-minute history");
}

void setupProfileGraph() {
  if (!profile_has_plan) return;
  if (chartHist && serSP && serTemp) {
    int16_t *sp_arr = lv_chart_get_y_array(chartHist, serSP);
    int16_t *t_arr  = lv_chart_get_y_array(chartHist, serTemp);
    for (int i = 0; i < GRAPH_SAMPLES; i++) {
      sp_arr[i] = (int16_t)roundf(profile_planned[i]);
      t_arr[i]  = LV_CHART_POINT_NONE;
    }
    // Reset the series' internal shift index — otherwise any idle-mode
    // set_next_value() history would render the plan rotated (first step
    // appearing mid-chart and last step wrapping to the left edge).
    lv_chart_set_x_start_point(chartHist, serSP,   0);
    lv_chart_set_x_start_point(chartHist, serTemp, 0);
    lv_chart_refresh(chartHist);
  }
  if (chartFull && serSPFull && serTempFull) {
    int16_t *sp_arr = lv_chart_get_y_array(chartFull, serSPFull);
    int16_t *t_arr  = lv_chart_get_y_array(chartFull, serTempFull);
    for (int i = 0; i < GRAPH_SAMPLES; i++) {
      sp_arr[i] = (int16_t)roundf(profile_planned[i]);
      t_arr[i]  = LV_CHART_POINT_NONE;
    }
    lv_chart_set_x_start_point(chartFull, serSPFull,   0);
    lv_chart_set_x_start_point(chartFull, serTempFull, 0);
    lv_chart_refresh(chartFull);
  }
  set_main_xaxis_profile(profile_total_duration_s);
  set_full_xaxis_profile(profile_total_duration_s);
}

void teardownProfileGraph() {
  profile_has_plan = false;
  profile_last_slot_filled = -1;
  if (chartHist && serSP && serTemp) {
    int16_t *sp_arr = lv_chart_get_y_array(chartHist, serSP);
    int16_t *t_arr  = lv_chart_get_y_array(chartHist, serTemp);
    for (int i = 0; i < GRAPH_SAMPLES; i++) {
      sp_arr[i] = LV_CHART_POINT_NONE;
      t_arr[i]  = LV_CHART_POINT_NONE;
    }
    lv_chart_set_x_start_point(chartHist, serSP,   0);
    lv_chart_set_x_start_point(chartHist, serTemp, 0);
    lv_chart_refresh(chartHist);
  }
  if (chartFull && serSPFull && serTempFull) {
    int16_t *sp_arr = lv_chart_get_y_array(chartFull, serSPFull);
    int16_t *t_arr  = lv_chart_get_y_array(chartFull, serTempFull);
    for (int i = 0; i < GRAPH_SAMPLES; i++) {
      sp_arr[i] = LV_CHART_POINT_NONE;
      t_arr[i]  = LV_CHART_POINT_NONE;
    }
    lv_chart_set_x_start_point(chartFull, serSPFull,   0);
    lv_chart_set_x_start_point(chartFull, serTempFull, 0);
    lv_chart_refresh(chartFull);
  }
  last_graph_sample_ms = millis();
  set_main_xaxis_idle();
  set_full_xaxis_idle();
}

void updateProfileGraphActual() {
  if (!profile_has_plan) return;
  if (profile_total_duration_s <= 0.0f) return;
  float elapsed = (millis() - profile_start_ms) / 1000.0f;
  int slot = (int)((elapsed / profile_total_duration_s) * (float)(GRAPH_SAMPLES - 1));
  if (slot < 0) slot = 0;
  if (slot >= GRAPH_SAMPLES) slot = GRAPH_SAMPLES - 1;
  int16_t val = (int16_t)roundf(current_temp);
  int start_s = (profile_last_slot_filled < 0) ? slot : profile_last_slot_filled + 1;
  if (chartHist && serTemp) {
    int16_t *t_arr = lv_chart_get_y_array(chartHist, serTemp);
    for (int s = start_s; s <= slot; s++) t_arr[s] = val;
    lv_chart_refresh(chartHist);
  }
  if (chartFull && serTempFull) {
    int16_t *t_arr = lv_chart_get_y_array(chartFull, serTempFull);
    for (int s = start_s; s <= slot; s++) t_arr[s] = val;
    lv_chart_refresh(chartFull);
  }
  profile_last_slot_filled = slot;
}

// ══════════════════════════════════════════════════════════════════
//   SECTION 9 — SETUP
// ══════════════════════════════════════════════════════════════════
void setup() {
  Serial.begin(115200);

  // Log reset reason for debugging random resets
  esp_reset_reason_t reason = esp_reset_reason();
  Serial.printf("\n[BOOT] Reset reason: %d ", (int)reason);
  switch (reason) {
    case ESP_RST_POWERON:  Serial.println("(Power-on)"); break;
    case ESP_RST_SW:       Serial.println("(Software)"); break;
    case ESP_RST_PANIC:    Serial.println("(Panic/exception)"); break;
    case ESP_RST_INT_WDT:  Serial.println("(Interrupt watchdog)"); break;
    case ESP_RST_TASK_WDT: Serial.println("(Task watchdog)"); break;
    case ESP_RST_WDT:      Serial.println("(Other watchdog)"); break;
    case ESP_RST_BROWNOUT: Serial.println("(Brownout)"); break;
    default:               Serial.println("(Other)"); break;
  }

  // GPIO
  pinMode(FAN_PIN, OUTPUT);
  digitalWrite(FAN_PIN, HIGH);
  delay(1000);
  pinMode(TRIAC_PIN, OUTPUT);
  digitalWrite(TRIAC_PIN, LOW);
  pinMode(ZCD_PIN, INPUT);
  pinMode(CS_PIN, OUTPUT);
  digitalWrite(CS_PIN, HIGH);

  // ZCD ISR — drives the zero-crossing sigma-delta modulator
  attachInterrupt(digitalPinToInterrupt(ZCD_PIN), zcd_isr, FALLING);

  // Preferences (control params + touch cal + saved NCR)
  preferences.begin("pid_data", false);
  setpoint   = 20.0;   // always cold at boot — never restored from NVS
  // Factory-default plant identification from the prototype oven. If NVS
  // already holds values from a successful serial `TUNE` run, those are
  // used; otherwise these defaults make the unit usable out of the box.
  //   Model: Integrating Process  (plant_tau = 0)
  //   k'    = 0.043215
  //   theta = 182.92 s
  //   Kc    = 0.063570
  //   Ti    = 1456.0432
  //   lambda= 3.0
  lambda_val = preferences.getFloat("lambda",   1.0f);
  plant_K    = preferences.getFloat("K",        0.156470f);
  plant_tau  = preferences.getFloat("tau",      0.0f);
  plant_theta= preferences.getFloat("theta",  82.5f);
  Kc         = preferences.getFloat("Kc",       0.058270f);
  Ti         = preferences.getFloat("Ti",    438.7191f);
  ts_min_x   = preferences.getShort("ts_minx", 300);
  ts_max_x   = preferences.getShort("ts_maxx", 3800);
  ts_min_y   = preferences.getShort("ts_miny", 300);
  ts_max_y   = preferences.getShort("ts_maxy", 3800);

  for (int i = 0; i < NCR_LUT_SIZE; i++) {
    char key[10];
    sprintf(key, "ncrh_%d", i);
    float sh = preferences.getFloat(key, 0.0f);
    ncr_nvs_heat[i]   = (sh > 0.0f);
    ncr_saved_heat[i] = ncr_nvs_heat[i] ? sh : NCR_DEFAULT_HEAT[i];
    ncr_lut_heat[i]   = ncr_saved_heat[i];

    sprintf(key, "ncrc_%d", i);
    float sc = preferences.getFloat(key, 0.0f);
    ncr_nvs_cool[i]   = (sc > 0.0f);
    ncr_saved_cool[i] = ncr_nvs_cool[i] ? sc : NCR_DEFAULT_COOL[i];
    ncr_lut_cool[i]   = ncr_saved_cool[i];

    yield();
  }
  // Always re-derive fitted LUTs from raw data on boot
  linearizeNCR(ncr_saved_heat, ncr_lin_heat, NCR_DEFAULT_HEAT, true);
  linearizeNCR(ncr_saved_cool, ncr_lin_cool, NCR_DEFAULT_COOL, false);
  saveLinearizedLUTs();

  loadCustomProfiles();
  loadSavedNets();
  wifiConnectAsync();    // fire-and-forget; check status in loop()

  // First temperature read (hardware SPI)
  current_temp = readMAX6675();
  if (isnan(current_temp)) current_temp = 25.0f;
  current_setpoint = setpoint;
  for (int i = 0; i < SLOPE_WINDOW; i++)   temp_history[i]  = current_temp;
  for (int i = 0; i < POWER_BUFFER_SIZE; i++) power_history[i] = 0.0;
  predicted_temp = current_temp;

  // TFT + touch
  tft.init();
  tft.setRotation(1);
  tft.fillScreen(TFT_BLACK);
  ts.begin();
  ts.setRotation(1);

  // LVGL
  lv_init();
  lv_disp_draw_buf_init(&lvDrawBuf, lvBuf1, lvBuf2, SCREEN_W * 20);

  static lv_disp_drv_t dispDrv;
  lv_disp_drv_init(&dispDrv);
  dispDrv.hor_res  = SCREEN_W;
  dispDrv.ver_res  = SCREEN_H;
  dispDrv.flush_cb = my_disp_flush;
  dispDrv.draw_buf = &lvDrawBuf;
  lv_disp_drv_register(&dispDrv);

  static lv_indev_drv_t indevDrv;
  lv_indev_drv_init(&indevDrv);
  indevDrv.type    = LV_INDEV_TYPE_POINTER;
  indevDrv.read_cb = my_touchpad_read;
  lv_indev_drv_register(&indevDrv);

  lv_theme_t *th = lv_theme_default_init(
    lv_disp_get_default(),
    lv_palette_main(LV_PALETTE_CYAN),
    lv_palette_main(LV_PALETTE_RED),
    true,
    &lv_font_inter_14);
  lv_disp_set_theme(lv_disp_get_default(), th);

  ui_init();

  Serial.println("\nSystem Ready. Waiting for commands.");
}

// ══════════════════════════════════════════════════════════════════
//   SECTION 10 — MAIN LOOP
// ══════════════════════════════════════════════════════════════════
void loop() {
  unsigned long now = millis();

  // 1. Control loop (250 ms)
  if (now - last_temp_read >= 250) {
    float raw_temp = readMAX6675();

    if (!isnan(raw_temp)) {
      temp_buffer[buffer_index] = raw_temp;
      buffer_index++;
      if (buffer_index >= MEDIAN_WINDOW) {
        buffer_index = 0;
        buffer_filled = true;
      }
      if (buffer_filled) {
        float median_temp = getMedian(temp_buffer, MEDIAN_WINDOW);
        current_temp = (EMA_ALPHA * median_temp) + ((1.0 - EMA_ALPHA) * current_temp);
      } else {
        current_temp = raw_temp;
      }
    } else {
      pid_output = 0.0;
      Serial.println("SENSOR ERROR! Halting heater.");
    }
    last_temp_read = now;

    if (is_ramping) {
      float step = ramp_rate_per_sec * 0.25;
      if (setpoint > current_setpoint) {
        current_setpoint += step;
        if (current_setpoint >= setpoint) {
          current_setpoint = setpoint;
          is_ramping = false;
          // The MPC's feedforward u_plan now provides the hold power.
          // Reset the trim integrator clean — computePID() will detect
          // the is_ramping transition and do the same, this is belt-and-
          // suspenders.
          error_integral = 0.0f;
          Serial.println("\n[RAMP] Target reached. Holding.");
        }
      } else {
        current_setpoint -= step;
        if (current_setpoint <= setpoint) {
          current_setpoint = setpoint;
          is_ramping = false;
          error_integral = 0.0f;
          Serial.println("\n[RAMP] Target reached. Holding.");
        }
      }
    }

    if (tune_state > 0) {
      runAutoTuner();
    } else {
      if (learn_state > 0) runLearnSequence();
      else if (profile_state > 0) runProfile();
      if (learn_state == 0 || learn_state == 2 || learn_state == 4) {
        computePID();
      } else if (learn_state == 3) {
        float bucket_lo = 20.0f + learn_target_bucket * 5.0f;
        if (current_temp < bucket_lo) computePID();
        else pid_output = 0.0;
      } else {
        pid_output = 0.0;
      }
    }

    // Convert pid_output → Q0.16 increment for the ZCD sigma-delta ISR.
    // All FP math stays on this side of the volatile fence.
    {
      float p = pid_output;
      if (p < 0.0f) p = 0.0f;
      else if (p > 1.0f) p = 1.0f;
      sd_increment = (uint16_t)(p * 65535.0f + 0.5f);
    }
  }

  // 2. Model-predictive ledger (1000 ms)
  if (now - last_history_time >= 1000) {
    if (history_filled) {
      current_slope = (current_temp - temp_history[history_index]) / (float)SLOPE_WINDOW;

      if (pid_output == 0.0 && current_slope < 0.0 && abs(current_slope) < (plant_K * 0.5) && learn_state != 3 && learn_state != 5 && profile_state == 0) {
        int bucket = (int)((current_temp - 20.0f) / 5.0f);
        if (bucket < 0) bucket = 0;
        if (bucket >= NCR_LUT_SIZE) bucket = NCR_LUT_SIZE - 1;
        ncr_lut_cool[bucket] = (0.1f * abs(current_slope)) + (0.9f * ncr_lut_cool[bucket]);

        if (bucket != ncr_active_bucket) {
          ncr_active_bucket = bucket;
          ncr_prev_ema = ncr_lut_cool[bucket];
          ncr_stable_start_ms = now;
        } else if (plant_theta > 0.0f) {
          float required_ms = 2.0f * plant_theta * 1000.0f;
          if ((float)(now - ncr_stable_start_ms) >= required_ms) {
            float delta_pct = abs(ncr_lut_cool[bucket] - ncr_prev_ema) / (ncr_prev_ema + 1e-9f);
            if (delta_pct < 0.05f) {
              float saved = ncr_saved_cool[bucket];
              float diff_pct = (saved > 0.0f) ? (abs(ncr_lut_cool[bucket] - saved) / saved) : 1.0f;
              if (diff_pct >= 0.10f) {
                char key[10];
                sprintf(key, "ncrc_%d", bucket);
                preferences.putFloat(key, ncr_lut_cool[bucket]);
                ncr_saved_cool[bucket] = ncr_lut_cool[bucket];
                ncr_nvs_cool[bucket] = true;
                Serial.print("\n[NCR] Saved cool bucket ");
                Serial.print(bucket); Serial.print(" (~");
                Serial.print(20 + bucket * 5); Serial.print("C): ");
                Serial.print(ncr_lut_cool[bucket], 6);
                Serial.println(" C/s");
              }
            }
            ncr_prev_ema = ncr_lut_cool[bucket];
            ncr_stable_start_ms = now;
          }
        }
      }
    }

    temp_history[history_index] = current_temp;
    history_index++;
    if (history_index >= SLOPE_WINDOW) {
      history_index = 0;
      history_filled = true;
    }

    power_history[power_history_index] = pid_output;
    power_history_index = (power_history_index + 1) % POWER_BUFFER_SIZE;

    last_history_time = now;
  }

  // 3. Telemetry (500 ms)
  if (now - last_telemetry_time >= 500) {
    last_telemetry_time = now;
    printTelemetry();
    ui_update();
  }

  // 4. Graph sampling
  //    Profile mode: update the actual-temp overlay frequently against the
  //                  precomputed planned trajectory.
  //    Idle mode:    rolling 60-min history, 30 s per sample.
  if (profile_state > 0 && profile_has_plan) {
    updateProfileGraphActual();
  } else if (!profile_has_plan) {
    if (now - last_graph_sample_ms >= GRAPH_PERIOD_MS) {
      last_graph_sample_ms = now;
      int16_t tmp = (int16_t)roundf(current_temp);
      int16_t sp  = (int16_t)roundf(current_setpoint);
      if (chartHist && serTemp && serSP) {
        lv_chart_set_next_value(chartHist, serTemp, tmp);
        lv_chart_set_next_value(chartHist, serSP,   sp);
      }
      if (chartFull && serTempFull && serSPFull) {
        lv_chart_set_next_value(chartFull, serTempFull, tmp);
        lv_chart_set_next_value(chartFull, serSPFull,   sp);
      }
    }
  }

  // 5. Profile plot (30 s, serial)
  if (profile_state > 0 && now - profile_plot_last_ms >= 30000UL) {
    profile_plot_last_ms = now;
    Serial.print(">>PLOT ");
    Serial.print((now - profile_start_ms) / 60000.0f, 3);
    Serial.print(" ");  Serial.print(current_temp, 2);
    Serial.print(" ");  Serial.print(predicted_temp, 2);
    Serial.print(" ");  Serial.print(pid_output, 4);
    Serial.print(" ");  Serial.print(current_setpoint, 2);
    Serial.print(" ");  Serial.print(profile_current_step + 1);
    Serial.print(" ");  Serial.println(profile_state);
  }

  // 6. Serial commands
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    handleCommand(cmd);
  }

  // 6b. WiFi connection state + one-shot OTA check after we first get online.
  {
    static bool     last_wifi_up          = false;
    static bool     ota_check_done        = false;
    static unsigned long wifi_rejoin_at   = 0;
    bool up = (WiFi.status() == WL_CONNECTED);
    if (up && !last_wifi_up) {
      Serial.print("[WIFI] Connected. IP=");
      Serial.println(WiFi.localIP());
      // TLS cert validation requires a real wall-clock. ESP32 boots with
      // time(NULL) ≈ 0, which is before every CA's NotBefore date — TLS
      // handshakes against github.io would fail with HTTP -1. Kick off
      // SNTP the moment we associate; UTC is fine for cert checks.
      configTime(0, 0, "pool.ntp.org", "time.nist.gov", "time.google.com");
      Serial.println("[NTP] Sync requested.");
    } else if (!up && last_wifi_up) {
      Serial.println("[WIFI] Link lost.");
    }
    // Repaint the SSID list on every association change so the connected
    // indicator (green SSID + green WiFi glyph) stays accurate live.
    if (up != last_wifi_up) refreshWifiList();
    last_wifi_up = up;
    wifi_connected_flag = up;

    // Harvest async scan results when they're ready (drives the SSID list
    // on scrWifi). Cheap when no scan is running.
    wifiPollScan();

    // ---- Connection-attempt state machine -------------------------------
    if (wifi_conn_state == WCS_TRYING) {
      wl_status_t s = WiFi.status();
      bool failed   = (s == WL_CONNECT_FAILED || s == WL_NO_SSID_AVAIL);
      bool timed_out = (now - wifi_conn_start_ms > WIFI_CONN_TIMEOUT_MS);
      if (s == WL_CONNECTED) {
        wifi_conn_state            = WCS_OK;
        wifi_conn_state_changed_ms = now;
        Serial.print("[WIFI] Connected to ");
        Serial.println(WiFi.SSID());
        refreshWifiList();
      } else if (failed || timed_out) {
        wifi_conn_state            = WCS_FAILED;
        wifi_conn_state_changed_ms = now;
        Serial.print("[WIFI] Connect failed (status=");
        Serial.print((int)s);
        Serial.println(timed_out ? ", timeout)" : ")");
        refreshWifiList();
        // Bounce the user to the password screen for a fresh attempt.
        // Only do this if they're still on scrWifi — if they navigated
        // away in the meantime we shouldn't yank focus.
        if (lv_scr_act() == scrWifi) {
          strncpy(wifi_ssid, wifi_conn_ssid, sizeof(wifi_ssid) - 1);
          wifi_ssid[sizeof(wifi_ssid) - 1] = 0;
          wifi_pass[0] = 0;
          wifi_retry_due_to_fail = true;
          show_scrWifiPass();
        }
      }
    } else if (wifi_conn_state == WCS_OK) {
      // Hold the green "Connected to X" banner briefly, then fade to idle.
      if (now - wifi_conn_state_changed_ms > WIFI_CONN_OK_HOLD_MS) {
        wifi_conn_state = WCS_IDLE;
        refreshWifiList();
      }
    }
    // Bump the title even when state hasn't transitioned, so "Scanning..."
    // appears/disappears live as wifiPollScan toggles wifi_scan_in_progress.
    static bool last_scan_in_progress = false;
    if (last_scan_in_progress != wifi_scan_in_progress) {
      last_scan_in_progress = wifi_scan_in_progress;
      refreshWifiList();
    }

    // Fire a single OTA check once the wall-clock is valid (or skip after
    // ~30 s of trying). Without a synced clock, setCACert() will refuse
    // the github.io chain and the manifest fetch returns HTTP -1.
    static unsigned long first_up_ms = 0;
    if (up && first_up_ms == 0) first_up_ms = now;
    if (up && !ota_check_done && first_up_ms != 0 && now - first_up_ms > 3000) {
      time_t t = time(nullptr);
      bool clock_valid = (t > 1700000000);   // > 2023-11-15 → SNTP done
      if (clock_valid) {
        ota_check_done = true;
        Serial.print("[NTP] Clock = ");
        Serial.println((long)t);
        checkForUpdate();
      } else if (now - first_up_ms > 30000) {
        ota_check_done = true;
        Serial.println("[OTA] Skipping — no NTP sync after 30 s.");
      }
    }

    // If we have creds but link dropped, retry every ~30 s.
    if (!up && wifi_ssid[0]) {
      if (wifi_rejoin_at == 0) wifi_rejoin_at = now + 30000UL;
      else if ((long)(now - wifi_rejoin_at) >= 0) {
        wifi_rejoin_at = now + 30000UL;
        WiFi.disconnect();
        WiFi.begin(wifi_ssid, wifi_pass);
      }
    } else {
      wifi_rejoin_at = 0;
    }
  }

  // 7. LVGL
  lv_tick_inc(5);
  lv_task_handler();
  delay(5);

  // 8. Execute pending OTA safely outside the UI thread
  if (execute_ota_update_now) {
    execute_ota_update_now = false;
    performUpdate();
  }
}

// ══════════════════════════════════════════════════════════════════
//   SECTION 11 — MPC CONTROLLER (dual-predictor + gain learning + PI hold)
// ══════════════════════════════════════════════════════════════════
// Plant model (autotuned, integrating with dead time):
//     dT/dt = gain * u(t - theta) - NCR(T)
//
// ── PHASE 0 — RAMP / approach ──────────────────────────────────────
// Feed-forward power, computed from plant gain + heat-side NCR:
//     u_ff = (signed_ramp_rate + NCR_heat(T)) / gain
// For a SET command (no commanded rate), u_ff = 1.0 — go full power.
//
// Two predictions run in parallel, both checked against `setpoint`
// every tick. Either one reaching setpoint hard-clamps u to 0.
//
//   1. calculated_temp   — open-loop simulator from the start of the
//                          ramp:
//        ramp_start_temp + gain·∑u·dt − ∑NCR·dt
//      Long-horizon, model-based. Knows about NCR loss explicitly.
//
//   2. predicted_temp    — Smith-style, slope-based:
//        current_temp + observed_slope·θ + gain·Δu_window
//      Short-horizon, observation-based. The momentum_slope cleanup
//      assumes our heater will counter natural cooling within θ.
//      This is the "predictor" exposed in telemetry (Pred: in the
//      serial log).
//
// ── Gain learning ─────────────────────────────────────────────────
// At replan, snapshot slope_at_replan = current_slope. After ~2·θ
// seconds (the slope has had time to respond to applied power), the
// observed Δslope = current_slope − slope_at_replan reflects how much
// the applied power actually moved the slope. Plant equation says
// Δslope ≈ gain · avg_power, so:
//     gain_estimate = Δslope / avg_power
// We blend that into learned_gain (50/50 LP) so subsequent ramps use
// a more accurate plant inversion. This is active "gain learning and
// compensating" — if real plant_K is e.g. 2.5× the autotuned value,
// learned_gain converges there over a few ramps and u_ff stops
// over-commanding.
//
// ── PHASE 1 — HOLD ────────────────────────────────────────────────
// Entered only after current_temp settles within 0.8°C of setpoint
// AND current_slope is flat. Power is:
//     u = NCR_avg(T)/gain + Kc·err + (Kc/Ti)·error_integral
// Average-NCR is the unbiased steady-state base; PI tunes out
// residual error precisely.
//
// Compatible with SET / RAMP / PROFILE: reads is_ramping, setpoint,
// current_setpoint, ramp_rate_per_sec as set by startProfileStep()
// and the serial command parser.
// --- MPC PID Computation ---
void computePID() {
  if (plant_K == 0.0) { pid_output = 0.0; return; }

  int theta_sec = round(plant_theta);
  int old_idx = (power_history_index - theta_sec + POWER_BUFFER_SIZE) % POWER_BUFFER_SIZE;
  float u_old = power_history[old_idx];
  float power_sum = 0.0;
  int idx = old_idx;
  for (int i = 0; i < theta_sec; i++) {
    idx = (idx + 1) % POWER_BUFFER_SIZE;
    power_sum += (power_history[idx] - u_old);
  }

  int ncr_bucket = (int)((current_temp - 20.0f) / 5.0f);
  if (ncr_bucket < 0) ncr_bucket = 0;
  if (ncr_bucket >= NCR_LUT_SIZE) ncr_bucket = NCR_LUT_SIZE - 1;
  float active_ncr = getActiveNCR(ncr_bucket);

  float momentum_slope = current_slope;
  if (momentum_slope < 0.0) {
    if (abs(momentum_slope) <= (active_ncr * 1.1)) momentum_slope = 0.0;
    else momentum_slope += active_ncr;
  }

  predicted_temp = current_temp + (momentum_slope * plant_theta) + (plant_K * power_sum);

  float dt = 0.25;

  float signed_ramp_rate = 0.0;
  if (is_ramping)
    signed_ramp_rate = (setpoint >= current_setpoint) ? ramp_rate_per_sec : -ramp_rate_per_sec;
  float future_setpoint = current_setpoint + (signed_ramp_rate * plant_theta);
  float p_error = future_setpoint - predicted_temp;
  float p_term = Kc * p_error;

  float i_error;
  float flat_threshold = plant_K * 0.1 * 0.3;

  if (abs(current_slope) <= flat_threshold && (current_setpoint - current_temp) <= (current_setpoint * 0.1) && (current_setpoint - current_temp) > (current_setpoint * 0.015)) {
    i_error = current_setpoint - current_temp;  flatThresholdFlag = 1;
  } else if ((current_setpoint - current_temp) <= (current_setpoint * 0.015) && current_temp < current_setpoint) {
    i_error = current_setpoint - current_temp;  flatThresholdFlag = 1;
  } else if (current_temp >= current_setpoint && predicted_temp >= (current_setpoint * 0.9)) {
    i_error = current_setpoint - current_temp;  flatThresholdFlag = 1;
  } else if (current_temp >= current_setpoint && predicted_temp < (current_setpoint * 0.9)) {
    i_error = current_setpoint - predicted_temp; flatThresholdFlag = 0;
  } else {
    i_error = current_setpoint - predicted_temp; flatThresholdFlag = 0;
  }

  error_integral += i_error * dt;
  float max_integral = (1.0 / Kc) * Ti;
  if (error_integral > max_integral) error_integral = max_integral;

  if (flatThresholdFlag && !prev_flat_flag) {
    float ss = steadyStateIntegral(current_setpoint);
    if (error_integral < ss) error_integral = ss;
  }
  prev_flat_flag = flatThresholdFlag;

  float u = p_term + (Kc * (1.0 / Ti) * error_integral);
  if (u >= 1.0) { u = 1.0; if (i_error > 0) error_integral -= i_error * dt; }
  else if (u <= 0.0) u = 0.0;
  if (error_integral < 0.0) error_integral = 0.0;
  pid_output = u;
}

// ══════════════════════════════════════════════════════════════════
//   SECTION 12 — AUTO-TUNER (unchanged)
// ══════════════════════════════════════════════════════════════════
void runAutoTuner() {
  unsigned long now = millis();
  switch (tune_state) {
    case 1:
      pid_output = 0.0;
      if (abs(current_temp - tune_start_temp) > 0.5) {
        tune_start_temp = current_temp; tune_start_time_ms = now;
      }
      if (now - tune_start_time_ms >= 60000) {
        tune_start_temp = current_temp;
        pid_output = tune_step_power;
        tune_start_time_ms = now;
        tune_state = 2;
        Serial.println("\n[TUNE] Steady state confirmed! Step applied. Finding Dead Time (theta)...");
      }
      break;
    case 2:
      if (current_temp >= tune_start_temp + 0.5) {
        plant_theta = (now - tune_start_time_ms) / 1000.0;
        temp_at_theta = current_temp;
        time_at_theta_ms = now;
        tune_state = 3;
        Serial.print("\n[TUNE] Dead Time (theta) found: ");
        Serial.println(plant_theta, 4);
        Serial.println("[TUNE] Observing maximum slope for 60 seconds...");
      }
      break;
    case 3:
      if (now - time_at_theta_ms >= 60000) {
        float delta_T = current_temp - temp_at_theta;
        float S_max = delta_T / 60.0;
        plant_K = S_max / tune_step_power;
        plant_tau = 0.0;
        Serial.println("\n[TUNE] Slope measurement complete. Calculating SIMC...");
        calculateSIMC();
        tune_state = 0;
        pid_output = 0.0;
      }
      break;
  }
}

void calculateSIMC() {
  float actual_lambda = plant_theta * (lambda_val * 0.33f);
  if (plant_tau == 0.0) {
    Kc = 1.0f / (plant_K * (actual_lambda + plant_theta));
    Ti = 4.0f * (actual_lambda + plant_theta);
  } else {
    Kc = (1.0f / plant_K) * (plant_tau / (actual_lambda + plant_theta));
    Ti = min(plant_tau, (float)(4.0f * (actual_lambda + plant_theta)));
  }
  preferences.putFloat("K",     plant_K);
  preferences.putFloat("tau",   plant_tau);
  preferences.putFloat("theta", plant_theta);
  preferences.putFloat("Kc",    Kc);
  preferences.putFloat("Ti",    Ti);
  Serial.println("\n--- Tuning Complete ---");
  printPlantData();
}

// ══════════════════════════════════════════════════════════════════
//   SECTION 13 — NCR LEARN SWEEP (unchanged)
// ══════════════════════════════════════════════════════════════════
float linearFitSlope(float* temps, int n) {
  float sum_x = 0, sum_y = 0, sum_xy = 0, sum_x2 = 0;
  for (int i = 0; i < n; i++) {
    sum_x += i;
    sum_y += temps[i];
    sum_xy += i * temps[i];
    sum_x2 += i * i;
  }
  float denom = n * sum_x2 - sum_x * sum_x;
  if (abs(denom) < 1e-9f) return 0.0f;
  return (n * sum_xy - sum_x * sum_y) / denom;
}

void learnAdvanceBucket() {
  learn_target_bucket++;
  if (learn_target_bucket >= NCR_LUT_SIZE) {
    // Heating sweep done — transition to cooldown phase
    Serial.println("\n[LEARN] *** Heating sweep complete! Starting cooldown phase... ***");
    setpoint = 200.0f;
    current_setpoint = 200.0f;
    is_ramping = false;
    error_integral = 0.0f;  // MPC feedforward owns the hold power
    learn_state = 4;
    learn_stable_start_ms = millis();
    learn_stable_temp = current_temp;
    Serial.println("[LEARN] Heating to 200C and waiting for settle...");
  } else {
    float next_sp = min(20.0f + learn_target_bucket * 5.0f + 4.0f, 200.0f);
    setpoint = next_sp;
    current_setpoint = next_sp;
    is_ramping = false;
    error_integral = 0.0f;  // MPC feedforward owns the hold power
    learn_state = 2;
    Serial.print("\n[LEARN] --> Bucket ");
    Serial.print(learn_target_bucket);
    Serial.print(" (~");
    Serial.print(20 + learn_target_bucket * 5);
    Serial.print("C). Heating to ");
    Serial.print(next_sp, 0);
    Serial.println("C...");
  }
}

void learnCoolAdvanceBucket() {
  learn_target_bucket--;
  if (learn_target_bucket < learn_start_bucket) {
    // Cooldown sweep done — linearize both LUTs and finish
    linearizeNCR(ncr_saved_heat, ncr_lin_heat, NCR_DEFAULT_HEAT, true);
    linearizeNCR(ncr_saved_cool, ncr_lin_cool, NCR_DEFAULT_COOL, false);
    saveLinearizedLUTs();

    learn_state = 0;
    setpoint = learn_room_temp;
    current_setpoint = learn_room_temp;
    is_ramping = false;
    error_integral = 0.0f;  // MPC feedforward owns the hold power
    Serial.println("\n[LEARN] *** Full sweep complete! Both LUTs learned & linearized. ***");
    Serial.print("[LEARN] Setpoint returned to room temp (");
    Serial.print(learn_room_temp, 1);
    Serial.println("C).");
    printPlantData();
  } else {
    // Next bucket will be reached naturally as temp drops
    learn_obs_count = 0;
    learn_prev_fitted_slope = 0.0;
    learn_obs_last_sample_ms = millis();
    learn_observe_start_ms = millis();
    Serial.print("\n[LEARN] --> Cool bucket ");
    Serial.print(learn_target_bucket);
    Serial.print(" (~");
    Serial.print(20 + learn_target_bucket * 5);
    Serial.println("C). Waiting for temp to drop...");
  }
}

void runLearnSequence() {
  unsigned long now = millis();
  switch (learn_state) {
    case 1:
      if (abs(current_temp - learn_stable_temp) > 0.5f) {
        learn_stable_temp = current_temp;
        learn_stable_start_ms = now;
      }
      if (now - learn_stable_start_ms >= 60000UL) {
        learn_room_temp = current_temp;
        learn_target_bucket = (int)((current_temp - 20.0f) / 5.0f);
        if (learn_target_bucket < 0) learn_target_bucket = 0;
        learn_start_bucket = learn_target_bucket;
        float first_sp = min(20.0f + learn_target_bucket * 5.0f + 4.0f, 200.0f);
        setpoint = first_sp; current_setpoint = first_sp;
        is_ramping = false; error_integral = 0.0f;  // MPC feedforward owns hold power
        learn_state = 2;
        Serial.print("\n[LEARN] Stable at "); Serial.print(learn_room_temp, 1);
        Serial.print("C. Starting heat-up sweep at bucket "); Serial.print(learn_target_bucket);
        Serial.print(" (SP="); Serial.print(first_sp, 0); Serial.println("C).");
      }
      break;

    case 2: {
      float target_sp = min(20.0f + learn_target_bucket * 5.0f + 4.0f, 200.0f);
      if (current_temp >= target_sp - 1.0f) {
        learn_obs_count = 0;
        learn_prev_fitted_slope = 0.0;
        learn_obs_last_sample_ms = now;
        learn_observe_start_ms = now;
        learn_state = 3;
        Serial.print("\n[LEARN] Heat bucket "); Serial.print(learn_target_bucket);
        Serial.print(" (~"); Serial.print(20 + learn_target_bucket * 5);
        Serial.println("C) reached. Heater OFF — observing heating NCR...");
      }
      break;
    }

    case 3: {
      float bucket_lo = 20.0f + learn_target_bucket * 5.0f;
      float bucket_hi = bucket_lo + 5.0f;

      if (current_temp > bucket_hi) {
        if (learn_obs_count > 0) {
          learn_obs_count = 0;
          Serial.println("\n[LEARN] Temp above bucket range. Waiting to drop...");
        }
        break;
      }
      if (current_temp < bucket_lo) {
        if (learn_obs_count > 0) {
          learn_obs_count = 0;
          Serial.println("\n[LEARN] Temp below bucket range. Reheating...");
        }
        break;
      }

      if (now - learn_obs_last_sample_ms >= 1000UL) {
        learn_obs_last_sample_ms = now;
        if (learn_obs_count < LEARN_OBS_WINDOW) {
          learn_obs_temps[learn_obs_count++] = current_temp;
        }
        if (learn_obs_count >= LEARN_OBS_WINDOW) {
          float fitted_slope = linearFitSlope(learn_obs_temps, LEARN_OBS_WINDOW);
          Serial.print("\n[LEARN] Fit: "); Serial.print(fitted_slope, 6);
          Serial.print(" "); Serial.print(current_temp, 2);
          Serial.print(" Bkt"); Serial.println(learn_target_bucket);
          if (fitted_slope < 0.0f) {
            if (learn_prev_fitted_slope < 0.0f) {
              float delta_pct = abs(fitted_slope - learn_prev_fitted_slope)
                                / (abs(learn_prev_fitted_slope) + 1e-9f);
              if (delta_pct < 0.10f) {
                float ncr_val = abs(fitted_slope);
                ncr_lut_heat[learn_target_bucket] = ncr_val;
                char key[10];
                sprintf(key, "ncrh_%d", learn_target_bucket);
                preferences.putFloat(key, ncr_val);
                ncr_saved_heat[learn_target_bucket] = ncr_val;
                ncr_nvs_heat[learn_target_bucket] = true;
                Serial.print("\n[LEARN] Heat bucket "); Serial.print(learn_target_bucket);
                Serial.print(" converged & saved: "); Serial.print(ncr_val, 6);
                Serial.println(" C/s");
                learnAdvanceBucket();
              } else {
                Serial.print("\n[LEARN] Heat bucket "); Serial.print(learn_target_bucket);
                Serial.print(" slope drift "); Serial.print(delta_pct * 100.0f, 1);
                Serial.println("%. Re-observing...");
                learn_prev_fitted_slope = fitted_slope;
                learn_obs_count = 0;
                learn_observe_start_ms = now;
              }
            } else {
              learn_prev_fitted_slope = fitted_slope;
              learn_obs_count = 0;
              learn_observe_start_ms = now;
            }
          } else {
            Serial.println("\n[LEARN] Slope not negative yet. Re-observing...");
            learn_obs_count = 0;
            learn_observe_start_ms = now;
          }
        }
      }
      break;
    }

    case 4: {
      // HEAT_TO_MAX: heat to 200C, wait for 60s stability
      if (current_temp >= 199.0f) {
        if (abs(current_temp - learn_stable_temp) > 0.5f) {
          learn_stable_temp = current_temp;
          learn_stable_start_ms = now;
        }
        if (now - learn_stable_start_ms >= 60000UL) {
          learn_target_bucket = NCR_LUT_SIZE - 1;
          learn_obs_count = 0;
          learn_prev_fitted_slope = 0.0;
          learn_obs_last_sample_ms = now;
          learn_observe_start_ms = now;
          learn_state = 5;
          Serial.println("\n[LEARN] Settled at 200C. Heater OFF — starting cooldown NCR sweep...");
          Serial.print("[LEARN] --> Cool bucket "); Serial.print(learn_target_bucket);
          Serial.print(" (~"); Serial.print(20 + learn_target_bucket * 5);
          Serial.println("C).");
        }
      } else {
        learn_stable_temp = current_temp;
        learn_stable_start_ms = now;
      }
      break;
    }

    case 5: {
      float bucket_lo = 20.0f + learn_target_bucket * 5.0f;
      float bucket_hi = bucket_lo + 5.0f;

      if (current_temp > bucket_hi) {
        if (learn_obs_count > 0) learn_obs_count = 0;
        break;
      }
      if (current_temp < bucket_lo) {
        Serial.print("\n[LEARN] Temp dropped below cool bucket ");
        Serial.print(learn_target_bucket);
        Serial.println(" range. Advancing...");
        learnCoolAdvanceBucket();
        break;
      }

      if (now - learn_obs_last_sample_ms >= 1000UL) {
        learn_obs_last_sample_ms = now;
        if (learn_obs_count < LEARN_OBS_WINDOW) {
          learn_obs_temps[learn_obs_count++] = current_temp;
        }
        if (learn_obs_count >= LEARN_OBS_WINDOW) {
          float fitted_slope = linearFitSlope(learn_obs_temps, LEARN_OBS_WINDOW);
          Serial.print("\n[LEARN] Fit: "); Serial.print(fitted_slope, 6);
          Serial.print(" "); Serial.print(current_temp, 2);
          Serial.print(" Bkt"); Serial.println(learn_target_bucket);
          if (fitted_slope < 0.0f) {
            if (learn_prev_fitted_slope < 0.0f) {
              float delta_pct = abs(fitted_slope - learn_prev_fitted_slope)
                                / (abs(learn_prev_fitted_slope) + 1e-9f);
              if (delta_pct < 0.10f) {
                float ncr_val = abs(fitted_slope);
                ncr_lut_cool[learn_target_bucket] = ncr_val;
                char key[10];
                sprintf(key, "ncrc_%d", learn_target_bucket);
                preferences.putFloat(key, ncr_val);
                ncr_saved_cool[learn_target_bucket] = ncr_val;
                ncr_nvs_cool[learn_target_bucket] = true;
                Serial.print("\n[LEARN] Cool bucket "); Serial.print(learn_target_bucket);
                Serial.print(" converged & saved: "); Serial.print(ncr_val, 6);
                Serial.println(" C/s");
                learnCoolAdvanceBucket();
              } else {
                Serial.print("\n[LEARN] Cool bucket "); Serial.print(learn_target_bucket);
                Serial.print(" slope drift "); Serial.print(delta_pct * 100.0f, 1);
                Serial.println("%. Re-observing...");
                learn_prev_fitted_slope = fitted_slope;
                learn_obs_count = 0;
                learn_observe_start_ms = now;
              }
            } else {
              learn_prev_fitted_slope = fitted_slope;
              learn_obs_count = 0;
              learn_observe_start_ms = now;
            }
          } else {
            Serial.println("\n[LEARN] Cool slope not negative yet. Re-observing...");
            learn_obs_count = 0;
            learn_observe_start_ms = now;
          }
        }
      }
      break;
    }
  }
}

// ══════════════════════════════════════════════════════════════════
//   SECTION 14 — PROFILE EXECUTION (unchanged)
// ══════════════════════════════════════════════════════════════════
void startProfileStep() {
  ProfileStep &s = profile_steps[profile_current_step];
  profile_state = 1;
  Serial.print("\n[PROFILE] Step "); Serial.print(profile_current_step + 1);
  Serial.print("/"); Serial.print(profile_step_count); Serial.print(": ");
  if (s.is_ramp) {
    setpoint = s.target;
    float planned_start = current_temp;
    if (profile_current_step > 0)
      planned_start = profile_steps[profile_current_step - 1].target;
    current_setpoint = planned_start;
    ramp_rate_per_sec = s.rate_per_sec;
    is_ramping = true;
    // MPC's feedforward u_plan = (rate + NCR_heat)/plant_K provides the
    // ramp power directly. The trim integrator starts clean — computePID
    // will re-zero it on the is_ramping transition anyway.
    error_integral = 0.0f;
    Serial.print("RAMP to "); Serial.print(s.target, 1);
    Serial.print("C @ "); Serial.print(s.rate_per_sec * 60.0f, 2);
    Serial.print("C/min, hold "); Serial.print(s.hold_sec / 60); Serial.println("min");
  } else {
    setpoint = s.target;
    current_setpoint = s.target;
    is_ramping = false;
    // MPC's feedforward u_plan = NCR_cool/plant_K provides the hold
    // power. The trim integrator starts clean.
    error_integral = 0.0f;
    Serial.print("SET "); Serial.print(s.target, 1);
    Serial.print("C, hold "); Serial.print(s.hold_sec / 60); Serial.println("min");
  }
}

void profileAdvanceStep() {
  profile_current_step++;
  if (profile_current_step >= profile_step_count) {
    profile_state = 0;
    // Always return to 20 °C when the profile ends — the oven must not
    // keep holding a warm setpoint once the run is over.
    setpoint          = 20.0f;
    current_setpoint  = 20.0f;
    is_ramping        = false;
    ramp_rate_per_sec = 0.0f;
    error_integral    = 0.0f;
    pid_output        = 0.0f;
    float elapsed_min = (millis() - profile_start_ms) / 60000.0f;
    Serial.println("\n[PROFILE] *** Complete! ***");
    Serial.print(">>PROFILE_DONE "); Serial.println(elapsed_min, 3);
    // Leave the planned+actual trace on the chart so the user can inspect
    // how the run actually tracked. It is wiped only when a new profile
    // is chosen (refresh_profile_preview) or on reset. profile_has_plan
    // stays true → idle sampling won't overwrite the frozen trace.
    profile_completed_popup_pending = true;
  } else {
    startProfileStep();
  }
}

void runProfile() {
  unsigned long now = millis();
  ProfileStep &s = profile_steps[profile_current_step];
  const bool is_last          = (profile_current_step == profile_step_count - 1);
  const bool is_cooldown_last = is_last && (s.target <= PROFILE_AMBIENT_BAND_HI);

  if (profile_state == 1) {
    bool arrived = s.is_ramp ? !is_ramping : (abs(current_temp - s.target) <= 2.0f);

    // For the final cooldown step, the ramp profiler finishing on schedule
    // doesn't actually mean the oven is cold — it just means the setpoint
    // walked down to target. Require the plate itself to be within 2 °C of
    // target, OR we accept the oven has reached ambient (see below).
    if (is_cooldown_last) {
      bool actually_cool = (fabsf(current_temp - s.target) <= 2.0f);
      if (arrived && !actually_cool) arrived = false;

      // Ambient-stuck detection: if the plate has been in the 20–40 °C
      // band continuously for 30 minutes, assume room temperature is above
      // the user's target and accept completion.
      if (!arrived &&
          current_temp >= PROFILE_AMBIENT_BAND_LO &&
          current_temp <= PROFILE_AMBIENT_BAND_HI) {
        if (profile_ambient_stable_since_ms == 0) {
          profile_ambient_stable_since_ms = now;
          Serial.print("\n[PROFILE] Final step — entering ambient watch at ");
          Serial.print(current_temp, 1);
          Serial.println(" \xC2\xB0""C.");
        } else if (now - profile_ambient_stable_since_ms >= PROFILE_AMBIENT_WAIT_MS) {
          Serial.print("\n[PROFILE] 30 min stable in ambient band (");
          Serial.print(current_temp, 1);
          Serial.println(" \xC2\xB0""C). Accepting as room temperature.");
          arrived = true;
        }
      } else if (!arrived) {
        profile_ambient_stable_since_ms = 0;
      }
    }

    if (arrived) {
      profile_ambient_stable_since_ms = 0;
      if (s.hold_sec == 0) profileAdvanceStep();
      else {
        profile_hold_start_ms = now;
        profile_state = 2;
        Serial.print("\n[PROFILE] Step "); Serial.print(profile_current_step + 1);
        Serial.print(" at target. Holding ");
        Serial.print(s.hold_sec / 60); Serial.println("min...");
      }
    }
  } else if (profile_state == 2) {
    if (now - profile_hold_start_ms >= s.hold_sec * 1000UL) profileAdvanceStep();
  }
}

// Helper: start a profile from an in-memory step list. Used by both
// the touchscreen UI and, indirectly, the PROFILE: serial command
// (which still parses inline — preserved below).
bool startProfileFromSteps(const ProfileStep *steps, int count, const char *source_name) {
  if (tune_state > 0 || learn_state > 0) {
    Serial.println("\nError: Cannot start profile while TUNE or LEARN is running.");
    return false;
  }
  if (plant_K == 0.0) {
    Serial.println("\nError: Run TUNE first.");
    return false;
  }
  if (count <= 0 || count > PROFILE_MAX_STEPS) {
    Serial.println("\nError: Invalid step count.");
    return false;
  }
  for (int i = 0; i < count; i++) profile_steps[i] = steps[i];
  profile_step_count = count;
  profile_current_step = 0;
  error_integral = 0.0;

  Serial.print("\n[PROFILE] Loaded "); Serial.print(count);
  Serial.print(" steps from: "); Serial.println(source_name ? source_name : "?");
  for (int i = 0; i < count; i++) {
    Serial.print("  "); Serial.print(i + 1); Serial.print(". ");
    if (profile_steps[i].is_ramp) {
      Serial.print("RAMP ");   Serial.print(profile_steps[i].target, 1);
      Serial.print("C @ ");    Serial.print(profile_steps[i].rate_per_sec * 60.0f, 2);
      Serial.print("C/min, hold "); Serial.print(profile_steps[i].hold_sec / 60);
    } else {
      Serial.print("SET ");    Serial.print(profile_steps[i].target, 1);
      Serial.print("C, hold "); Serial.print(profile_steps[i].hold_sec / 60);
    }
    Serial.println("min");
  }

  profile_start_ms                 = millis();
  profile_plot_last_ms             = millis();
  profile_ambient_stable_since_ms  = 0;
  Serial.print(">>PROFILE_START ");
  Serial.print(count); Serial.print(" ");
  Serial.println(current_temp, 2);
  for (int i = 0; i < count; i++) {
    Serial.print(">>STEP ");
    Serial.print(profile_steps[i].is_ramp ? "RAMP" : "SET");
    Serial.print(" "); Serial.print(profile_steps[i].target, 1);
    Serial.print(" "); Serial.print(profile_steps[i].rate_per_sec * 60.0f, 4);
    Serial.print(" "); Serial.println(profile_steps[i].hold_sec / 60.0f, 4);
  }
  Serial.print(">>PLOT 0.000 ");
  Serial.print(current_temp, 2);
  Serial.print(" ");  Serial.print(current_temp, 2);
  Serial.print(" ");  Serial.print(pid_output, 4);
  Serial.print(" ");  Serial.print(current_setpoint, 2);
  Serial.print(" 1 ");  Serial.println(profile_state);

  computePlannedTrajectory(profile_steps, count, current_temp);
  setupProfileGraph();
  startProfileStep();
  return true;
}

void stopProfile(const char *reason) {
  profile_state                    = 0;
  is_ramping                       = false;
  ramp_rate_per_sec                = 0.0f;
  setpoint                         = 20.0f;
  current_setpoint                 = 20.0f;
  error_integral                   = 0.0f;
  pid_output                       = 0.0f;
  sd_increment                     = 0;
  profile_ambient_stable_since_ms  = 0;
  Serial.print("\n[PROFILE] Aborted");
  if (reason) { Serial.print(" ("); Serial.print(reason); Serial.print(")"); }
  Serial.println(".");
  // Preserve the partial trace on the chart — the user may want to inspect
  // what was captured. The graph is cleared only when a new profile is
  // selected or the device is reset.
}

// ══════════════════════════════════════════════════════════════════
//   SECTION 15 — SERIAL COMMAND PARSER (unchanged)
// ══════════════════════════════════════════════════════════════════
void handleCommand(String cmd) {
  if (cmd == "TUNE") {
    Serial.println("\nStarting Auto-Tune. Waiting for temperature to stabilize (60s)...");
    tune_state = 1;
    tune_start_time_ms = millis();
    tune_start_temp = current_temp;
    error_integral = 0;
  } else if (cmd == "LEARN") {
    if (plant_K == 0.0) {
      Serial.println("\nError: Run TUNE first — plant model is required for LEARN.");
    } else if (tune_state > 0) {
      Serial.println("\nError: Auto-tune in progress. Wait for it to finish.");
    } else if (profile_state > 0) {
      Serial.println("\nError: Profile running. Send PROFILE: STOP first.");
    } else {
      learn_state = 1;
      learn_stable_start_ms = millis();
      learn_stable_temp = current_temp;
      pid_output = 0.0;
      sd_increment = 0;
      error_integral = 0.0;
      Serial.println("\n[LEARN] Starting dual NCR sweep (heat-up then cool-down).");
      Serial.println("[LEARN] Waiting 60s for room-temp stability...");
    }
  } else if (cmd.startsWith("SET ")) {
    float val = cmd.substring(4).toFloat();
    if (val >= 20.0 && val <= 200.0) {
      profile_state = 0;
      setpoint = val;
      current_setpoint = val;
      is_ramping = false;
      ramp_rate_per_sec = 0.0;
      error_integral = 0.0f;  // MPC feedforward owns the hold power
      Serial.print("\nSetpoint updated to: "); Serial.println(setpoint, 4);
    } else {
      Serial.println("\nError: Setpoint must be 20-200.");
    }
  } else if (cmd.startsWith("RAMP ")) {
    int spaceIdx = cmd.indexOf(' ', 5);
    if (spaceIdx < 0) {
      Serial.println("\nError: Usage: RAMP <setpoint> <rate_C_per_min>  e.g. RAMP 100 5.0");
    } else {
      float target = cmd.substring(5, spaceIdx).toFloat();
      float rate_per_min = cmd.substring(spaceIdx + 1).toFloat();
      if (target < 20.0 || target > 200.0) {
        Serial.println("\nError: Ramp target must be 20-200.");
      } else if (rate_per_min <= 0.0) {
        Serial.println("\nError: Ramp rate must be > 0 °C/min.");
      } else {
        profile_state = 0;
        setpoint = target;
        current_setpoint = current_temp;
        ramp_rate_per_sec = rate_per_min / 60.0;
        is_ramping = true;

        error_integral = 0.0f;  // MPC feedforward owns the ramp power
        Serial.print("\n[RAMP] Target: ");    Serial.print(setpoint, 1);
        Serial.print(" C | Rate: ");          Serial.print(rate_per_min, 2);
        Serial.print(" C/min (");             Serial.print(ramp_rate_per_sec, 4);
        Serial.println(" C/s) | Starting from current temp.");
      }
    }
  } else if (cmd.startsWith("PROFILE:")) {
    String body = cmd.substring(8); body.trim();
    if (body.equalsIgnoreCase("STOP")) {
      stopProfile("serial STOP");
    } else if (tune_state > 0 || learn_state > 0) {
      Serial.println("\nError: Cannot start profile while TUNE or LEARN is running.");
    } else if (plant_K == 0.0) {
      Serial.println("\nError: Run TUNE first.");
    } else {
      ProfileStep parsed[PROFILE_MAX_STEPS];
      int count = 0;
      bool parse_ok = true;
      int pos = 0;
      while (pos <= (int)body.length() && count < PROFILE_MAX_STEPS) {
        int comma = body.indexOf(',', pos);
        String tok = (comma < 0) ? body.substring(pos) : body.substring(pos, comma);
        tok.trim();
        if (tok.length() > 0) {
          if (tok.startsWith("RAMP ")) {
            String r = tok.substring(5); r.trim();
            int s1 = r.indexOf(' ');  if (s1 < 0) { parse_ok=false; break; }
            float tgt = r.substring(0, s1).toFloat();
            r = r.substring(s1 + 1); r.trim();
            int s2 = r.indexOf(' ');  if (s2 < 0) { parse_ok=false; break; }
            float rate = r.substring(0, s2).toFloat();
            float hold_min = r.substring(s2 + 1).toFloat();
            if (tgt<20||tgt>200||rate<=0||hold_min<0) { parse_ok=false; break; }
            parsed[count].is_ramp = true;
            parsed[count].target = tgt;
            parsed[count].rate_per_sec = rate / 60.0f;
            parsed[count].hold_sec = (unsigned long)(hold_min * 60.0f);
            count++;
          } else if (tok.startsWith("SET ")) {
            String r = tok.substring(4); r.trim();
            int s1 = r.indexOf(' ');  if (s1 < 0) { parse_ok=false; break; }
            float tgt = r.substring(0, s1).toFloat();
            float hold_min = r.substring(s1 + 1).toFloat();
            if (tgt<20||tgt>200||hold_min<0) { parse_ok=false; break; }
            parsed[count].is_ramp = false;
            parsed[count].target = tgt;
            parsed[count].rate_per_sec = 0.0f;
            parsed[count].hold_sec = (unsigned long)(hold_min * 60.0f);
            count++;
          } else { parse_ok=false; break; }
        }
        if (comma < 0) break;
        pos = comma + 1;
      }
      if (!parse_ok || count == 0) {
        Serial.println("\nError: Invalid PROFILE syntax.");
        Serial.println("Usage: PROFILE: RAMP <temp> <C/min> <hold_min>, SET <temp> <hold_min>, ...");
      } else {
        startProfileFromSteps(parsed, count, "serial PROFILE:");
        snprintf(selected_profile_name, PROFILE_NAME_LEN, "serial");
        profile_is_selected = true;
        set_profile_button_label(selected_profile_name);
      }
    }
  } else if (cmd.startsWith("LAMBDA ")) {
    float val = cmd.substring(7).toFloat();
    if (val >= 1.0 && val <= 5.0) {
      lambda_val = val;
      preferences.putFloat("lambda", lambda_val);
      if (plant_K > 0) calculateSIMC();
      Serial.print("\nLambda updated to: "); Serial.println(lambda_val, 4);
    } else {
      Serial.println("\nError: Lambda must be 1-5.");
    }
  } else if (cmd == "PLANT") {
    Serial.println(); printPlantData();
  } else if (cmd == "SHOT") {
    // Capture whatever screen is currently displayed. The host-side
    // tools/screenshot.py reassembles the tile stream into a PNG.
    screenshot_capture_current();
  } else if (cmd == "SHOT ALL") {
    // Cycle every built screen, capturing each in turn. Useful for
    // generating the full website asset set in one go. Skips scrKeypad
    // (transient overlay) and restores scrMain at the end.
    lv_obj_t *shots[] = {
      scrMain, scrMaterial, scrHousehold, scrEngineer,
      scrCustom, scrCustomDetail, scrBuilder, scrAddType,
      scrFullGraph, scrSettings, scrCalibrate, scrRename,
      scrWifi, scrWifiPass, scrOTA
    };
    const size_t n = sizeof(shots) / sizeof(shots[0]);
    for (size_t i = 0; i < n; i++) {
      if (!shots[i]) continue;
      lv_scr_load(shots[i]);
      lv_refr_now(lv_disp_get_default());   // settle the load before snapshotting
      screenshot_capture_current();
    }
    lv_scr_load(scrMain);
  }
}

// ══════════════════════════════════════════════════════════════════
//   SECTION 16 — TELEMETRY (unchanged)
// ══════════════════════════════════════════════════════════════════
void printTelemetry() {
  Serial.print("Temp: "); Serial.print(current_temp, 4);
  Serial.print(" C (Pred: "); Serial.print(predicted_temp, 1);
  Serial.print(") | SP: "); Serial.print(current_setpoint, 2);
  if (is_ramping) {
    Serial.print(" -> "); Serial.print(setpoint, 1);
    Serial.print(" ("); Serial.print(ramp_rate_per_sec * 60.0, 2);
    Serial.print(" C/min)");
  }
  Serial.print(" | True RMS Out: "); Serial.print(pid_output * 100.0, 2); Serial.print(" %");
  if (tune_state > 0) {
    float elapsed = (millis() - tune_start_time_ms) / 1000.0;
    Serial.print(" | Mode: TUNING (State "); Serial.print(tune_state);
    Serial.print(") | Tmr: "); Serial.print(elapsed, 1); Serial.print(" s");
  } else if (profile_state > 0 && profile_current_step < profile_step_count) {
    ProfileStep &ps = profile_steps[profile_current_step];
    Serial.print(" | Mode: PROFILE "); Serial.print(profile_current_step + 1);
    Serial.print("/"); Serial.print(profile_step_count);
    Serial.print(ps.is_ramp ? " RAMP" : " SET");
    if (profile_state == 1) {
      Serial.print(" -> "); Serial.print(ps.target, 1); Serial.print("C");
    } else {
      float elapsed_min = (millis() - profile_hold_start_ms) / 60000.0f;
      Serial.print(" HOLD "); Serial.print(elapsed_min, 1);
      Serial.print("/"); Serial.print(ps.hold_sec / 60); Serial.print("min");
    }
  } else if (learn_state > 0) {
    Serial.print(" | Mode: LEARN S"); Serial.print(learn_state);
    Serial.print(" Bkt"); Serial.print(learn_target_bucket);
    Serial.print("(~"); Serial.print(20 + learn_target_bucket * 5); Serial.print("C)");
    if (learn_state == 3 || learn_state == 5) {
      Serial.print(" obs "); Serial.print(learn_obs_count);
      Serial.print("/"); Serial.print(LEARN_OBS_WINDOW); Serial.print("s");
    }
  } else if (plant_K == 0.0) {
    Serial.print(" | Mode: IDLE (Needs TUNE)");
  } else if (is_ramping) {
    Serial.print(" | Mode: RAMP | ErrInt: "); Serial.print(error_integral, 4);
    Serial.print(flatThresholdFlag ? " [REAL]" : " [PRED]");
  } else {
    Serial.print(" | Mode: PID | ErrInt: "); Serial.print(error_integral, 4);
    Serial.print(flatThresholdFlag ? " [REAL]" : " [PRED]");
  }
  Serial.println();
}

void printPlantData() {
  Serial.println("--- Plant Data ---");
  if (plant_tau == 0.0) {
    Serial.println("Model: Integrating Process");
    Serial.print("Gain (k'): "); Serial.println(plant_K, 6);
  } else {
    Serial.println("Model: FOPDT");
    Serial.print("Gain (K): "); Serial.println(plant_K, 6);
    Serial.print("Time Constant (tau): "); Serial.println(plant_tau, 4);
  }
  Serial.print("Dead Time (theta): "); Serial.println(plant_theta, 4);
  Serial.println("--- PID Parameters ---");
  Serial.print("Kc: "); Serial.println(Kc, 6);
  Serial.print("Ti: "); Serial.println(Ti, 4);
  Serial.print("Lambda Setting: "); Serial.println(lambda_val, 4);
  Serial.println("--- NCR Heat-Up Table (C/s) ---");
  Serial.println("  Temp |  Raw Heat | Curve Fit | Status");
  for (int i = 0; i < NCR_LUT_SIZE; i++) {
    int temp_c = 20 + i * 5;
    Serial.print("  "); if (temp_c < 100) Serial.print(" ");
    Serial.print(temp_c); Serial.print("C | ");
    Serial.print(ncr_lut_heat[i], 6); Serial.print(" | ");
    Serial.print(ncr_lin_heat[i], 6); Serial.print(" | ");
    Serial.println(ncr_nvs_heat[i] ? "learned" : "default");
  }
  Serial.println("--- NCR Cool-Down Table (C/s) ---");
  Serial.println("  Temp |  Raw Cool | Linearizd | Status");
  for (int i = 0; i < NCR_LUT_SIZE; i++) {
    int temp_c = 20 + i * 5;
    Serial.print("  "); if (temp_c < 100) Serial.print(" ");
    Serial.print(temp_c); Serial.print("C | ");
    Serial.print(ncr_lut_cool[i], 6); Serial.print(" | ");
    Serial.print(ncr_lin_cool[i], 6); Serial.print(" | ");
    Serial.println(ncr_nvs_cool[i] ? "learned" : "default");
  }
  Serial.println("----------------------");
}

// ══════════════════════════════════════════════════════════════════
//   SECTION 17 — LVGL DISPLAY / TOUCH CALLBACKS
// ══════════════════════════════════════════════════════════════════

// Resolve the currently-loaded screen object to a stable identifier so
// the host script can name captured PNG files after the screen they show.
static const char *current_screen_name() {
  lv_obj_t *s = lv_scr_act();
  if (s == scrMain)         return "main";
  if (s == scrMaterial)     return "material";
  if (s == scrHousehold)    return "household";
  if (s == scrEngineer)     return "engineer";
  if (s == scrCustom)       return "custom";
  if (s == scrCustomDetail) return "custom_detail";
  if (s == scrBuilder)      return "builder";
  if (s == scrAddType)      return "add_type";
  if (s == scrKeypad)       return "keypad";
  if (s == scrFullGraph)    return "full_graph";
  if (s == scrSettings)     return "settings";
  if (s == scrCalibrate)    return "calibrate";
  if (s == scrRename)       return "rename";
  if (s == scrWifi)         return "wifi";
  if (s == scrWifiPass)     return "wifi_pass";
  if (s == scrOTA)          return "ota";
  return "unknown";
}

// Capture the currently-displayed screen. Prints a text BEGIN marker,
// then forces a synchronous full-screen refresh — my_disp_flush emits a
// TILE marker + raw RGB565 bytes for every flush — then prints an END
// marker. lv_refr_now() blocks the loop so no other Serial output can
// interleave with the binary tiles.
static void screenshot_capture_current() {
  Serial.print("<<SHOT_BEGIN w="); Serial.print(SCREEN_W);
  Serial.print(" h=");             Serial.print(SCREEN_H);
  // Memory byte order of lv_color_t depends on LV_COLOR_16_SWAP — when
  // it's set LVGL stores colors pre-swapped (panel-native big-endian);
  // otherwise it's host little-endian. Advertise the actual layout so
  // the host decoder doesn't have to guess.
  Serial.print(" fmt=");
#if LV_COLOR_16_SWAP
  Serial.print("rgb565_be");
#else
  Serial.print("rgb565_le");
#endif
  Serial.print(" name=");
  Serial.print(current_screen_name());
  Serial.println(">>");

  g_shot_active = true;
  lv_obj_invalidate(lv_scr_act());
  lv_refr_now(lv_disp_get_default());
  g_shot_active = false;

  Serial.println("<<SHOT_END>>");
}

void my_disp_flush(lv_disp_drv_t *disp, const lv_area_t *area, lv_color_t *color_p) {
  uint32_t w = area->x2 - area->x1 + 1;
  uint32_t h = area->y2 - area->y1 + 1;

  if (g_shot_active) {
    uint32_t bytes = (uint32_t)w * h * sizeof(lv_color_t);
    Serial.print("<<SHOT_TILE x="); Serial.print(area->x1);
    Serial.print(" y=");            Serial.print(area->y1);
    Serial.print(" w=");            Serial.print(w);
    Serial.print(" h=");            Serial.print(h);
    Serial.print(" bytes=");        Serial.print(bytes);
    Serial.println(">>");
    // Stream the raw framebuffer tile. Serial.write blocks until the
    // UART TX FIFO has room, so this throttles itself to the line rate.
    const uint8_t *p   = (const uint8_t *)color_p;
    uint32_t       rem = bytes;
    while (rem) {
      size_t chunk = rem > 256 ? 256 : rem;
      Serial.write(p, chunk);
      p   += chunk;
      rem -= chunk;
    }
    Serial.println();  // CRLF terminator so the host can resync
  }

  tft.startWrite();
  tft.setAddrWindow(area->x1, area->y1, w, h);
  tft.pushColors((uint16_t *)&color_p->full, w * h, true);
  tft.endWrite();
  lv_disp_flush_ready(disp);
}

void my_touchpad_read(lv_indev_drv_t *indev, lv_indev_data_t *data) {
  if (ts.touched()) {
    TS_Point p = ts.getPoint();
    if (p.z > 300) {
      data->point.x = constrain(map(p.x, ts_min_x, ts_max_x, 0, SCREEN_W), 0, SCREEN_W - 1);
      data->point.y = constrain(map(p.y, ts_min_y, ts_max_y, 0, SCREEN_H), 0, SCREEN_H - 1);
      data->state = LV_INDEV_STATE_PR;
    } else data->state = LV_INDEV_STATE_REL;
  } else data->state = LV_INDEV_STATE_REL;
}

// ══════════════════════════════════════════════════════════════════
//   SECTION 18 — UI HELPERS
// ══════════════════════════════════════════════════════════════════
// Wrap the profile-select button label: split on the first "/" if present
// (consuming an adjacent space for neatness), otherwise split at the space
// closest to the middle. Short names pass through unchanged.
static void set_profile_button_label(const char *text) {
  if (!lblBtnProfile) return;
  if (!text) text = "";
  int len = (int)strlen(text);
  if (len <= 14) { lv_label_set_text(lblBtnProfile, text); return; }

  int split = -1;
  const char *slash = strchr(text, '/');
  if (slash) {
    split = (int)(slash - text);
    // Prefer breaking at the space that already separates the slash from
    // the word before it so the "/" visually starts the second line.
    if (split > 0 && text[split - 1] == ' ') split--;
  } else {
    int mid = len / 2;
    int best = -1, best_dist = 9999;
    for (int i = 0; i < len; i++) {
      if (text[i] == ' ') {
        int d = abs(i - mid);
        if (d < best_dist) { best_dist = d; best = i; }
      }
    }
    split = best;
  }

  if (split < 0) { lv_label_set_text(lblBtnProfile, text); return; }

  char buf[PROFILE_NAME_LEN + 4];
  int out = 0;
  for (int i = 0; i < split && out < (int)sizeof(buf) - 1; i++) buf[out++] = text[i];
  if (out < (int)sizeof(buf) - 1) buf[out++] = '\n';
  // Skip a single space at the break point so the second line doesn't start
  // with leading whitespace (for the "nearest-space" case).
  int start = split;
  if (text[start] == ' ') start++;
  for (int i = start; i < len && out < (int)sizeof(buf) - 1; i++) buf[out++] = text[i];
  buf[out] = 0;
  lv_label_set_text(lblBtnProfile, buf);
}

static bool heaterActive() {
  return profile_state > 0 || is_ramping || tune_state > 0 ||
         learn_state == 2 || learn_state == 4 ||
         setpoint > 25.0f || pid_output > 0.02f;
}

// Apply a consistent screen-level background + padding.
static void style_screen(lv_obj_t *scr) {
  lv_obj_set_style_bg_color(scr, lv_color_hex(CLR_BG), 0);
  lv_obj_set_style_bg_opa  (scr, LV_OPA_COVER, 0);
  lv_obj_set_style_pad_all (scr, 0, 0);
}

// Compact top-left Back button — used on every sub-screen for consistent nav.
static lv_obj_t *add_back_button(lv_obj_t *parent, lv_event_cb_t cb) {
  lv_obj_t *b = lv_btn_create(parent);
  lv_obj_set_size(b, 56, 30);
  lv_obj_set_pos(b, 4, 4);
  lv_obj_set_style_bg_color    (b, lv_color_hex(CLR_PANEL),   0);
  lv_obj_set_style_bg_color    (b, lv_color_hex(CLR_PANEL2),  LV_STATE_PRESSED);
  lv_obj_set_style_border_color(b, lv_color_hex(CLR_BORDER),  0);
  lv_obj_set_style_border_width(b, 1, 0);
  lv_obj_set_style_radius      (b, 5, 0);
  lv_obj_set_style_shadow_width(b, 0, 0);
  lv_obj_set_style_text_color  (b, lv_color_hex(CLR_TXT),     0);
  lv_obj_add_event_cb(b, cb, LV_EVENT_CLICKED, NULL);
  lv_obj_t *l = lv_label_create(b);
  lv_label_set_text(l, LV_SYMBOL_LEFT "  Back");
  lv_obj_set_style_text_font(l, &lv_font_inter_14, 0);
  lv_obj_center(l);
  return b;
}

// Title-bar label at the top of any sub-screen.
static lv_obj_t *add_title(lv_obj_t *parent, const char *text) {
  lv_obj_t *t = lv_label_create(parent);
  lv_label_set_text(t, text);
  lv_obj_set_style_text_color(t, lv_color_hex(CLR_TXT), 0);
  lv_obj_set_style_text_font (t, &lv_font_inter_16, 0);
  lv_obj_align(t, LV_ALIGN_TOP_MID, 0, 10);
  // Thin underline — placed below the 30-px Back button (y=4..34) so it
  // doesn't clip through the button body.
  lv_obj_t *line = lv_obj_create(parent);
  lv_obj_set_size(line, SCREEN_W - 20, 1);
  lv_obj_set_pos(line, 10, 38);
  lv_obj_set_style_bg_color (line, lv_color_hex(CLR_BORDER), 0);
  lv_obj_set_style_border_width(line, 0, 0);
  lv_obj_clear_flag(line, LV_OBJ_FLAG_CLICKABLE | LV_OBJ_FLAG_SCROLLABLE);
  return t;
}

// Themed flat button factory with role-based color.
static lv_obj_t *make_themed_btn(lv_obj_t *parent, const char *text,
                                 int x, int y, int w, int h,
                                 lv_event_cb_t cb, void *user_data,
                                 BtnRole role) {
  lv_obj_t *b = lv_btn_create(parent);
  lv_obj_set_size(b, w, h);
  lv_obj_set_pos(b, x, y);

  uint32_t bg = CLR_ACCENT_D, bgp = CLR_ACCENT, brd = CLR_ACCENT;
  switch (role) {
    case ROLE_PRIMARY:   bg = CLR_ACCENT_D;  bgp = CLR_ACCENT;   brd = CLR_ACCENT;   break;
    case ROLE_SECONDARY: bg = CLR_PANEL2;    bgp = CLR_NEUTRAL;  brd = CLR_BORDER;   break;
    case ROLE_SUCCESS:   bg = CLR_SUCCESS_D; bgp = CLR_SUCCESS;  brd = CLR_SUCCESS;  break;
    case ROLE_DANGER:    bg = CLR_DANGER_D;  bgp = CLR_DANGER;   brd = CLR_DANGER;   break;
    case ROLE_NEUTRAL:   bg = CLR_PANEL;     bgp = CLR_PANEL2;   brd = CLR_BORDER;   break;
    case ROLE_AMBER:     bg = CLR_AMBER_D;   bgp = CLR_AMBER;    brd = CLR_AMBER;    break;
  }
  lv_obj_set_style_bg_color (b, lv_color_hex(bg),  0);
  lv_obj_set_style_bg_color (b, lv_color_hex(bgp), LV_STATE_PRESSED);
  lv_obj_set_style_border_color(b, lv_color_hex(brd), 0);
  lv_obj_set_style_border_width(b, 1, 0);
  lv_obj_set_style_radius  (b, 6, 0);
  lv_obj_set_style_shadow_width(b, 0, 0);
  lv_obj_set_style_text_color(b, lv_color_hex(CLR_TXT), 0);

  lv_obj_add_event_cb(b, cb, LV_EVENT_CLICKED, user_data);

  lv_obj_t *l = lv_label_create(b);
  lv_label_set_text(l, text);
  lv_obj_set_style_text_font(l, &lv_font_inter_14, 0);
  lv_obj_center(l);
  return b;
}

// Fwd decls for blink-related state used below.
static void blink_timer_cb(lv_timer_t *t);

// ══════════════════════════════════════════════════════════════════
//   SECTION 19 — MESSAGE BOX OVERLAY (alert / confirm)
// ══════════════════════════════════════════════════════════════════
static lv_obj_t *msgbox   = NULL;
static lv_obj_t *msgbox_dim = NULL;

static void msgbox_kill() {
  if (msgbox)     { lv_obj_del(msgbox);     msgbox = NULL; }
  if (msgbox_dim) { lv_obj_del(msgbox_dim); msgbox_dim = NULL; }
}
static void msgbox_close_cb(lv_event_t *e)   { msgbox_kill(); }
static void msgbox_confirm_cb(lv_event_t *e) {
  lv_event_cb_t ok_cb = (lv_event_cb_t)lv_event_get_user_data(e);
  msgbox_kill();
  if (ok_cb) ok_cb(e);
}

static lv_obj_t *make_msgbox_shell(uint32_t accent_color) {
  msgbox_kill();
  // Scrim
  msgbox_dim = lv_obj_create(lv_layer_top());
  lv_obj_set_size(msgbox_dim, SCREEN_W, SCREEN_H);
  lv_obj_set_pos(msgbox_dim, 0, 0);
  lv_obj_set_style_bg_color(msgbox_dim, lv_color_black(), 0);
  lv_obj_set_style_bg_opa  (msgbox_dim, LV_OPA_60, 0);
  lv_obj_set_style_border_width(msgbox_dim, 0, 0);
  lv_obj_set_style_radius  (msgbox_dim, 0, 0);
  lv_obj_clear_flag(msgbox_dim, LV_OBJ_FLAG_SCROLLABLE);

  // Panel
  msgbox = lv_obj_create(lv_layer_top());
  lv_obj_set_size(msgbox, 300, 170);
  lv_obj_center(msgbox);
  lv_obj_set_style_bg_color    (msgbox, lv_color_hex(CLR_PANEL),  0);
  lv_obj_set_style_border_color(msgbox, lv_color_hex(accent_color), 0);
  lv_obj_set_style_border_width(msgbox, 2, 0);
  lv_obj_set_style_radius      (msgbox, 8, 0);
  lv_obj_set_style_pad_all     (msgbox, 10, 0);
  lv_obj_clear_flag(msgbox, LV_OBJ_FLAG_SCROLLABLE);
  return msgbox;
}

void ui_show_alert(const char *title, const char *body) {
  lv_obj_t *box = make_msgbox_shell(CLR_DANGER);

  lv_obj_t *t = lv_label_create(box);
  lv_label_set_text(t, title);
  lv_obj_set_style_text_color(t, lv_color_hex(CLR_DANGER), 0);
  lv_obj_set_style_text_font(t, &lv_font_inter_16, 0);
  lv_obj_align(t, LV_ALIGN_TOP_MID, 0, 0);

  lv_obj_t *b = lv_label_create(box);
  lv_label_set_text(b, body);
  lv_label_set_long_mode(b, LV_LABEL_LONG_WRAP);
  lv_obj_set_width(b, 260);
  lv_obj_set_style_text_color(b, lv_color_hex(CLR_TXT), 0);
  lv_obj_set_style_text_font(b, &lv_font_inter_14, 0);
  lv_obj_align(b, LV_ALIGN_TOP_MID, 0, 28);

  make_themed_btn(box, "OK", 90, 100, 100, 40,
                  msgbox_close_cb, NULL, ROLE_PRIMARY);
}

// Success / informational popup — themed green, single OK button.
void ui_show_info(const char *title, const char *body) {
  lv_obj_t *box = make_msgbox_shell(CLR_SUCCESS);

  lv_obj_t *t = lv_label_create(box);
  lv_label_set_text(t, title);
  lv_obj_set_style_text_color(t, lv_color_hex(CLR_SUCCESS), 0);
  lv_obj_set_style_text_font(t, &lv_font_inter_16, 0);
  lv_obj_align(t, LV_ALIGN_TOP_MID, 0, 0);

  lv_obj_t *b = lv_label_create(box);
  lv_label_set_text(b, body);
  lv_label_set_long_mode(b, LV_LABEL_LONG_WRAP);
  lv_obj_set_width(b, 260);
  lv_obj_set_style_text_color(b, lv_color_hex(CLR_TXT), 0);
  lv_obj_set_style_text_font(b, &lv_font_inter_14, 0);
  lv_obj_align(b, LV_ALIGN_TOP_MID, 0, 28);

  make_themed_btn(box, "OK", 90, 100, 100, 40,
                  msgbox_close_cb, NULL, ROLE_SUCCESS);
}

// About / contact overlay triggered by tapping the READARK logo.
// Shows a QR pointing at the channel, an "About Us" caption, and a close
// button. Sits on lv_layer_top() so it overlays every screen.
void ui_show_about() {
  lv_obj_t *box = make_msgbox_shell(CLR_ACCENT);
  lv_obj_set_size(box, 200, 224);
  lv_obj_center(box);

  lv_obj_t *qr = lv_qrcode_create(box, 140,
                                  lv_color_hex(0x000000),
                                  lv_color_hex(0xFFFFFF));
  static const char *ABOUT_URL =
      "https://www.youtube.com/watch?v=qWVc-xVZxho";
  lv_qrcode_update(qr, ABOUT_URL, strlen(ABOUT_URL));
  lv_obj_align(qr, LV_ALIGN_TOP_MID, 0, 0);

  lv_obj_t *cap = lv_label_create(box);
  lv_label_set_text(cap, "About Us");
  lv_obj_set_style_text_color(cap, lv_color_hex(CLR_TXT), 0);
  lv_obj_set_style_text_font (cap, &lv_font_inter_14, 0);
  lv_obj_align(cap, LV_ALIGN_TOP_MID, 0, 146);

  make_themed_btn(box, "Close", 45, 168, 90, 32,
                  msgbox_close_cb, NULL, ROLE_NEUTRAL);
}

void ui_show_messagebox(const char *title, const char *body,
                        const char *btn_ok, const char *btn_cancel,
                        lv_event_cb_t ok_cb) {
  lv_obj_t *box = make_msgbox_shell(CLR_AMBER);
  // Taller box so multi-line prompts (e.g. the auto-tune confirmation)
  // don't collide with the action buttons.
  lv_obj_set_size(box, 300, 210);
  lv_obj_center(box);

  lv_obj_t *t = lv_label_create(box);
  lv_label_set_text(t, title);
  lv_obj_set_style_text_color(t, lv_color_hex(CLR_AMBER), 0);
  lv_obj_set_style_text_font(t, &lv_font_inter_16, 0);
  lv_obj_align(t, LV_ALIGN_TOP_MID, 0, 0);

  lv_obj_t *b = lv_label_create(box);
  lv_label_set_text(b, body);
  lv_label_set_long_mode(b, LV_LABEL_LONG_WRAP);
  lv_obj_set_width(b, 270);
  lv_obj_set_style_text_color(b, lv_color_hex(CLR_TXT), 0);
  lv_obj_set_style_text_font(b, &lv_font_inter_14, 0);
  lv_obj_align(b, LV_ALIGN_TOP_MID, 0, 28);

  make_themed_btn(box, btn_ok,     5, 140, 130, 40,
                  msgbox_confirm_cb, (void *)ok_cb, ROLE_DANGER);
  make_themed_btn(box, btn_cancel, 145, 140, 130, 40,
                  msgbox_close_cb, NULL, ROLE_NEUTRAL);
}

// ══════════════════════════════════════════════════════════════════
//   SECTION 20 — MAIN SCREEN
// ══════════════════════════════════════════════════════════════════
static void btn_profile_clicked(lv_event_t *e)  {
  // Profile selection is blocked while a profile is running — picking a
  // different one mid-run would be confusing and potentially dangerous.
  // Tell the user to stop the current run first.
  if (profile_state > 0) {
    ui_show_alert("Profile running",
                  "Stop the current profile before selecting a new one.");
    return;
  }
  show_scrMaterial();
}
static void really_stop_cb(lv_event_t *e)       { stopProfile("user STOP"); }

static void btn_startstop_clicked(lv_event_t *e) {
  if (profile_state > 0) {
    ui_show_messagebox("Cancel profile?",
                       "A thermal profile is currently running. Are you sure you want to cancel it?",
                       "Cancel it", "Keep running", really_stop_cb);
    return;
  }
  if (!profile_is_selected) {
    ui_show_alert("No profile", "Please select a thermal profile first.");
    return;
  }
  // Saved-custom takes priority (its name may collide with auto-generated strings).
  if (selected_custom_idx >= 0 && selected_custom_idx < saved_custom_count) {
    SavedCustom &sc = saved_customs[selected_custom_idx];
    if (sc.step_count == 0) {
      ui_show_alert("Empty", "Selected custom profile has no steps.");
      return;
    }
    startProfileFromSteps(sc.steps, sc.step_count, sc.name);
    return;
  }
  // Predefined
  for (int i = 0; i < HOUSEHOLD_COUNT; i++) {
    if (strcmp(HOUSEHOLD_PROFILES[i].name, selected_profile_name) == 0) {
      startProfileFromSteps(HOUSEHOLD_PROFILES[i].steps,
                            HOUSEHOLD_PROFILES[i].step_count,
                            HOUSEHOLD_PROFILES[i].name);
      return;
    }
  }
  for (int i = 0; i < ENG_COUNT; i++) {
    if (strcmp(ENGINEERING_PROFILES[i].name, selected_profile_name) == 0) {
      startProfileFromSteps(ENGINEERING_PROFILES[i].steps,
                            ENGINEERING_PROFILES[i].step_count,
                            ENGINEERING_PROFILES[i].name);
      return;
    }
  }
  ui_show_alert("Unknown profile", "Selected profile could not be found.");
}

// Forward decl used in main-screen graph tap handler
static void btn_fullgraph_cb(lv_event_t *e) { show_scrFullGraph(); }
static void btn_settings_cb (lv_event_t *e) { show_scrSettings(); }

// READARK logo rendered on the main page where the title would usually be.
// Uncomment the declaration + the two lines in build_scrMain() once the
// asset file (readark_logo.c) has been dropped into the sketch folder —
// see the chat recipe. Until then we skip the symbol to keep the linker
// happy.
LV_IMG_DECLARE(readark_logo);

static void build_scrMain() {
  scrMain = lv_obj_create(NULL);
  style_screen(scrMain);
  lv_obj_clear_flag(scrMain, LV_OBJ_FLAG_SCROLLABLE);

  // ============ TOP BAR ============
  // Slightly lighter strip behind the gear / logo so the top bar reads as a
  // distinct UI region rather than blending into the screen background.
  lv_obj_t *topBar = lv_obj_create(scrMain);
  lv_obj_set_size(topBar, SCREEN_W, 36);
  lv_obj_set_pos(topBar, 0, 0);
  lv_obj_set_style_bg_color    (topBar, lv_color_hex(CLR_TOP_BAR), 0);
  lv_obj_set_style_bg_opa      (topBar, LV_OPA_COVER, 0);
  lv_obj_set_style_border_width(topBar, 0, 0);
  lv_obj_set_style_radius      (topBar, 0, 0);
  lv_obj_set_style_pad_all     (topBar, 0, 0);
  lv_obj_clear_flag(topBar, LV_OBJ_FLAG_CLICKABLE | LV_OBJ_FLAG_SCROLLABLE);

  // Settings gear (top-left)
  lv_obj_t *btnSettings = lv_btn_create(scrMain);
  lv_obj_set_size(btnSettings, 38, 32);
  lv_obj_set_pos(btnSettings, 3, 3);
  lv_obj_set_style_bg_color    (btnSettings, lv_color_hex(CLR_PANEL),  0);
  lv_obj_set_style_bg_color    (btnSettings, lv_color_hex(CLR_PANEL2), LV_STATE_PRESSED);
  lv_obj_set_style_border_color(btnSettings, lv_color_hex(CLR_BORDER), 0);
  lv_obj_set_style_border_width(btnSettings, 1, 0);
  lv_obj_set_style_radius      (btnSettings, 5, 0);
  lv_obj_set_style_shadow_width(btnSettings, 0, 0);
  lv_obj_set_style_text_color  (btnSettings, lv_color_hex(CLR_ACCENT), 0);
  lv_obj_add_event_cb(btnSettings, btn_settings_cb, LV_EVENT_CLICKED, NULL);
  lv_obj_t *lblS = lv_label_create(btnSettings);
  lv_label_set_text(lblS, LV_SYMBOL_SETTINGS);
  lv_obj_set_style_text_font(lblS, &lv_font_inter_16, 0);
  lv_obj_center(lblS);

  // READARK logo — drops into the top bar where a title would normally go.
  // Re-enable once readark_logo.c is in the sketch folder and the matching
  // LV_IMG_DECLARE above is uncommented.
  lv_obj_t *imgLogo = lv_img_create(scrMain);
  lv_img_set_src(imgLogo, &readark_logo);
  // Centered vertically in the 36-px top bar; nudged slightly right of
  // screen center so the settings gear doesn't visually crowd it.
  {
    const int top_bar_h = 36;
    const int logo_h    = readark_logo.header.h;
    lv_obj_align(imgLogo, LV_ALIGN_TOP_MID, 6, (top_bar_h - logo_h) / 2);
  }
  // Tap the logo to open the About / QR overlay.
  lv_obj_add_flag(imgLogo, LV_OBJ_FLAG_CLICKABLE);
  lv_obj_add_event_cb(imgLogo,
    [](lv_event_t *e) { ui_show_about(); },
    LV_EVENT_CLICKED, NULL);

  // ============ GAUGE (left, padded from top bar) ============
  lv_obj_t *gaugePanel = lv_obj_create(scrMain);
  lv_obj_set_size(gaugePanel, 155, 143);
  lv_obj_set_pos(gaugePanel, 3, 40);
  lv_obj_set_style_bg_color    (gaugePanel, lv_color_hex(CLR_PANEL),  0);
  lv_obj_set_style_border_color(gaugePanel, lv_color_hex(CLR_BORDER), 0);
  lv_obj_set_style_border_width(gaugePanel, 1, 0);
  lv_obj_set_style_radius      (gaugePanel, 8, 0);
  lv_obj_set_style_pad_all     (gaugePanel, 0, 0);
  lv_obj_clear_flag(gaugePanel, LV_OBJ_FLAG_SCROLLABLE);

  arcTemp = lv_arc_create(gaugePanel);
  lv_obj_set_size(arcTemp, 125, 125);
  lv_obj_align(arcTemp, LV_ALIGN_TOP_MID, 0, 8);
  lv_arc_set_range(arcTemp, 20, 200);
  lv_arc_set_bg_angles(arcTemp, 135, 45);
  lv_arc_set_rotation(arcTemp, 0);
  lv_arc_set_value(arcTemp, 20);
  lv_obj_remove_style(arcTemp, NULL, LV_PART_KNOB);
  lv_obj_clear_flag(arcTemp, LV_OBJ_FLAG_CLICKABLE);
  lv_obj_set_style_arc_color(arcTemp, lv_color_hex(CLR_GRID),   LV_PART_MAIN);
  lv_obj_set_style_arc_color(arcTemp, lv_color_hex(CLR_ACCENT), LV_PART_INDICATOR);
  lv_obj_set_style_arc_width(arcTemp, 9, LV_PART_MAIN);
  lv_obj_set_style_arc_width(arcTemp, 9, LV_PART_INDICATOR);
  lv_obj_set_style_arc_rounded(arcTemp, true, LV_PART_INDICATOR);

  lblTempVal = lv_label_create(gaugePanel);
  lv_label_set_text(lblTempVal, "20\xC2\xB0");
  lv_obj_set_style_text_color(lblTempVal, lv_color_hex(CLR_TXT), 0);
  lv_obj_set_style_text_font(lblTempVal, &lv_font_inter_24, 0);
  lv_obj_align_to(lblTempVal, arcTemp, LV_ALIGN_CENTER, 0, -8);

  lblSetpoint = lv_label_create(gaugePanel);
  lv_label_set_text(lblSetpoint, "SP 20\xC2\xB0");
  lv_obj_set_style_text_color(lblSetpoint, lv_color_hex(CLR_ACCENT), 0);
  lv_obj_set_style_text_font(lblSetpoint, &lv_font_inter_14, 0);
  lv_obj_align_to(lblSetpoint, arcTemp, LV_ALIGN_CENTER, 0, 16);

  lblMode = lv_label_create(gaugePanel);
  lv_label_set_text(lblMode, "IDLE");
  lv_obj_set_style_text_color(lblMode, lv_color_hex(CLR_TXT_DIM), 0);
  lv_obj_set_style_text_font(lblMode, &lv_font_inter_14, 0);
  lv_obj_align(lblMode, LV_ALIGN_BOTTOM_MID, 0, -4);

  // Small blinking warning glyph inside the gauge panel — top-right corner,
  // away from the arc's sweep. Hidden unless the heater is actively running.
  lblGaugeWarn = lv_label_create(gaugePanel);
  lv_label_set_text(lblGaugeWarn, LV_SYMBOL_CHARGE);
  lv_obj_set_style_text_color(lblGaugeWarn, lv_color_hex(CLR_DANGER), 0);
  lv_obj_set_style_text_font (lblGaugeWarn, &lv_font_inter_16, 0);
  lv_obj_align(lblGaugeWarn, LV_ALIGN_TOP_RIGHT, -6, 4);
  lv_obj_add_flag(lblGaugeWarn, LV_OBJ_FLAG_HIDDEN);

  // ============ GRAPH (right, tappable → fullscreen) ============
  lv_obj_t *graphPanel = lv_obj_create(scrMain);
  lv_obj_set_size(graphPanel, 156, 143);
  lv_obj_set_pos(graphPanel, 161, 40);
  lv_obj_set_style_bg_color    (graphPanel, lv_color_hex(CLR_PANEL),  0);
  lv_obj_set_style_border_color(graphPanel, lv_color_hex(CLR_BORDER), 0);
  lv_obj_set_style_border_width(graphPanel, 1, 0);
  lv_obj_set_style_radius      (graphPanel, 8, 0);
  lv_obj_set_style_pad_all     (graphPanel, 0, 0);
  lv_obj_clear_flag(graphPanel, LV_OBJ_FLAG_SCROLLABLE);
  lv_obj_add_flag  (graphPanel, LV_OBJ_FLAG_CLICKABLE);
  lv_obj_add_event_cb(graphPanel, btn_fullgraph_cb, LV_EVENT_CLICKED, NULL);

  chartHist = lv_chart_create(graphPanel);
  lv_obj_set_size(chartHist, 150, 108);
  lv_obj_set_pos(chartHist, 3, 3);
  lv_chart_set_type(chartHist, LV_CHART_TYPE_LINE);
  lv_chart_set_point_count(chartHist, GRAPH_SAMPLES);
  // Range 0–200 so horizontal grid-lines at 50/100/150 land exactly on
  // multiples of 50 °C. The chart's own top border serves as the 200 mark.
  lv_chart_set_range(chartHist, LV_CHART_AXIS_PRIMARY_Y, 0, 200);
  lv_chart_set_update_mode(chartHist, LV_CHART_UPDATE_MODE_SHIFT);
  // 3 horizontal dividers in a range of 200 → gridlines every 50 °C.
  lv_chart_set_div_line_count(chartHist, 3, 4);
  // No built-in axis_tick: the widget was drawing a spurious line at the
  // top edge during the first render (before any real data existed), which
  // showed up as the "actual-starts-at-the-top" artifact on boot.
  lv_obj_set_style_size(chartHist, 0, LV_PART_INDICATOR);
  lv_obj_set_style_bg_color    (chartHist, lv_color_hex(CLR_PANEL2),  0);
  lv_obj_set_style_border_color(chartHist, lv_color_hex(CLR_BORDER),  0);
  lv_obj_set_style_border_width(chartHist, 1, 0);
  lv_obj_set_style_line_color  (chartHist, lv_color_hex(CLR_GRID),    LV_PART_MAIN);
  lv_obj_set_style_line_width  (chartHist, 1,                         LV_PART_MAIN);
  lv_obj_set_style_pad_left    (chartHist, 4, 0);
  lv_obj_set_style_pad_right   (chartHist, 4, 0);
  lv_obj_set_style_pad_top     (chartHist, 2, 0);
  lv_obj_set_style_pad_bottom  (chartHist, 3, 0);
  lv_obj_set_style_line_width  (chartHist, 2, LV_PART_ITEMS);
  lv_obj_clear_flag(chartHist, LV_OBJ_FLAG_CLICKABLE); // let taps pass to panel
  serSP   = lv_chart_add_series(chartHist, lv_color_hex(CLR_PLANNED), LV_CHART_AXIS_PRIMARY_Y);
  serTemp = lv_chart_add_series(chartHist, lv_color_hex(CLR_ACTUAL),  LV_CHART_AXIS_PRIMARY_Y);
  // Defensive: LVGL's own series init *should* produce POINT_NONE for every
  // slot, but on some builds the first render paints a phantom line at the
  // top of the chart. Force the entire array to POINT_NONE up-front.
  {
    int16_t *sp_arr = lv_chart_get_y_array(chartHist, serSP);
    int16_t *t_arr  = lv_chart_get_y_array(chartHist, serTemp);
    for (int i = 0; i < GRAPH_SAMPLES; i++) {
      sp_arr[i] = LV_CHART_POINT_NONE;
      t_arr[i]  = LV_CHART_POINT_NONE;
    }
    lv_chart_set_x_start_point(chartHist, serSP,   0);
    lv_chart_set_x_start_point(chartHist, serTemp, 0);
    lv_chart_refresh(chartHist);
  }

  // "200" label in the top-left corner of the plot area. This is the only
  // Y-axis label on the small chart — the internal gridlines at 50/100/150
  // implicitly carry the scale.
  lv_obj_t *lblY200 = lv_label_create(graphPanel);
  lv_label_set_text(lblY200, "200");
  lv_obj_set_style_text_color(lblY200, lv_color_hex(CLR_TXT_DIM), 0);
  lv_obj_set_style_text_font (lblY200, &lv_font_inter_12, 0);
  lv_obj_set_style_bg_color  (lblY200, lv_color_hex(CLR_PANEL), 0);
  lv_obj_set_style_bg_opa    (lblY200, LV_OPA_70, 0);
  lv_obj_set_style_pad_hor   (lblY200, 2, 0);
  lv_obj_set_style_radius    (lblY200, 2, 0);
  lv_obj_set_pos(lblY200, 8, 6);

  // X-axis labels — up to 4 widgets, dynamically positioned by the
  // axis-helpers below so that visible values are always multiples of 10
  // at equal tick spacings.
  for (int i = 0; i < MAIN_X_MAX_LABELS; i++) {
    lblXAxis[i] = lv_label_create(graphPanel);
    lv_label_set_text(lblXAxis[i], "");
    lv_obj_set_style_text_color(lblXAxis[i], lv_color_hex(CLR_TXT_DIM), 0);
    lv_obj_set_style_text_font (lblXAxis[i], &lv_font_inter_12, 0);
    lv_obj_add_flag(lblXAxis[i], LV_OBJ_FLAG_HIDDEN);
  }

  // Legend
  lv_obj_t *legPlan = lv_obj_create(graphPanel);
  lv_obj_set_size(legPlan, 8, 8);
  lv_obj_set_pos(legPlan, 4, 128);
  lv_obj_set_style_bg_color(legPlan, lv_color_hex(CLR_PLANNED), 0);
  lv_obj_set_style_border_width(legPlan, 0, 0);
  lv_obj_set_style_radius(legPlan, 1, 0);
  lv_obj_clear_flag(legPlan, LV_OBJ_FLAG_SCROLLABLE | LV_OBJ_FLAG_CLICKABLE);

  lv_obj_t *legAct = lv_obj_create(graphPanel);
  lv_obj_set_size(legAct, 8, 8);
  lv_obj_set_pos(legAct, 74, 128);
  lv_obj_set_style_bg_color(legAct, lv_color_hex(CLR_ACTUAL), 0);
  lv_obj_set_style_border_width(legAct, 0, 0);
  lv_obj_set_style_radius(legAct, 1, 0);
  lv_obj_clear_flag(legAct, LV_OBJ_FLAG_SCROLLABLE | LV_OBJ_FLAG_CLICKABLE);

  lv_obj_t *l1 = lv_label_create(graphPanel);
  lv_label_set_text(l1, "plan");
  lv_obj_set_style_text_font(l1, &lv_font_inter_12, 0);
  lv_obj_set_style_text_color(l1, lv_color_hex(CLR_TXT_DIM), 0);
  lv_obj_set_pos(l1, 15, 126);

  lv_obj_t *l2 = lv_label_create(graphPanel);
  lv_label_set_text(l2, "actual");
  lv_obj_set_style_text_font(l2, &lv_font_inter_12, 0);
  lv_obj_set_style_text_color(l2, lv_color_hex(CLR_TXT_DIM), 0);
  lv_obj_set_pos(l2, 86, 126);

  // Expand-icon hint in the top-right of the graph panel
  lv_obj_t *expIcon = lv_label_create(graphPanel);
  lv_label_set_text(expIcon, LV_SYMBOL_EYE_OPEN);
  lv_obj_set_style_text_font(expIcon, &lv_font_inter_14, 0);
  lv_obj_set_style_text_color(expIcon, lv_color_hex(CLR_TXT_DIM), 0);
  lv_obj_align(expIcon, LV_ALIGN_TOP_RIGHT, -4, 3);
  lv_obj_clear_flag(expIcon, LV_OBJ_FLAG_CLICKABLE);

  // ============ BUTTONS (bottom) ============
  btnProfile = make_themed_btn(scrMain, "Select Profile",
                               3, 188, 155, 48,
                               btn_profile_clicked, NULL, ROLE_PRIMARY);
  lblBtnProfile = lv_obj_get_child(btnProfile, 0);
  lv_obj_set_style_text_font(lblBtnProfile, &lv_font_inter_16, 0);

  btnStartStop = make_themed_btn(scrMain, "START",
                                 162, 188, 155, 48,
                                 btn_startstop_clicked, NULL, ROLE_SUCCESS);
  lblBtnStart = lv_obj_get_child(btnStartStop, 0);
  lv_obj_set_style_text_font(lblBtnStart, &lv_font_inter_16, 0);
}

// ══════════════════════════════════════════════════════════════════
//   SECTION 21 — MATERIAL CATEGORY SCREEN
// ══════════════════════════════════════════════════════════════════
static void back_to_main_cb(lv_event_t *e)      { show_scrMain(); }
static void cat_household_cb(lv_event_t *e)     { show_scrHousehold(); }
static void cat_engineer_cb(lv_event_t *e)      { eng_page = 0; show_scrEngineer(); }
static void cat_custom_cb(lv_event_t *e)        { custom_list_page = 0; show_scrCustom(); }
static void back_to_material_cb(lv_event_t *e)  { show_scrMaterial(); }

static void build_scrMaterial() {
  scrMaterial = lv_obj_create(NULL);
  style_screen(scrMaterial);
  lv_obj_clear_flag(scrMaterial, LV_OBJ_FLAG_SCROLLABLE);
  add_back_button(scrMaterial, back_to_main_cb);
  add_title(scrMaterial, "Material Category");

  make_themed_btn(scrMaterial, "Household",   15,  52, 290, 55, cat_household_cb, NULL, ROLE_PRIMARY);
  make_themed_btn(scrMaterial, "Engineering", 15, 117, 290, 55, cat_engineer_cb,  NULL, ROLE_PRIMARY);
  make_themed_btn(scrMaterial, "Custom",      15, 182, 290, 55, cat_custom_cb,    NULL, ROLE_AMBER);
}

// ══════════════════════════════════════════════════════════════════
//   SECTION 22 — HOUSEHOLD SCREEN (PLA, PETG)
// ══════════════════════════════════════════════════════════════════
static void pick_household(int idx) {
  strncpy(selected_profile_name, HOUSEHOLD_PROFILES[idx].name, PROFILE_NAME_LEN - 1);
  selected_profile_name[PROFILE_NAME_LEN - 1] = 0;
  profile_is_selected = true;
  selected_custom_idx = -1;
  set_profile_button_label(selected_profile_name);
  refresh_profile_preview();
  show_scrMain();
}
static void hh_pla_cb (lv_event_t *e) { pick_household(0); }
static void hh_petg_cb(lv_event_t *e) { pick_household(1); }

static void build_scrHousehold() {
  scrHousehold = lv_obj_create(NULL);
  style_screen(scrHousehold);
  lv_obj_clear_flag(scrHousehold, LV_OBJ_FLAG_SCROLLABLE);
  add_back_button(scrHousehold, back_to_material_cb);
  add_title(scrHousehold, "Household");

  make_themed_btn(scrHousehold, "PLA",  15,  60, 290, 80, hh_pla_cb,  NULL, ROLE_PRIMARY);
  make_themed_btn(scrHousehold, "PETG", 15, 150, 290, 80, hh_petg_cb, NULL, ROLE_PRIMARY);
}

// ══════════════════════════════════════════════════════════════════
//   SECTION 23 — ENGINEERING SCREEN (paged list, arrow-navigated)
// ══════════════════════════════════════════════════════════════════
static void eng_entry_cb(lv_event_t *e) {
  int slot = (int)(intptr_t)lv_event_get_user_data(e);
  int idx = eng_page * ENG_PER_PAGE + slot;
  if (idx < 0 || idx >= ENG_COUNT) return;
  strncpy(selected_profile_name, ENGINEERING_PROFILES[idx].name, PROFILE_NAME_LEN - 1);
  selected_profile_name[PROFILE_NAME_LEN - 1] = 0;
  profile_is_selected = true;
  selected_custom_idx = -1;
  set_profile_button_label(selected_profile_name);
  refresh_profile_preview();
  show_scrMain();
}
static void eng_up_cb(lv_event_t *e) { if (eng_page > 0) { eng_page--; refresh_eng_page(); } }
static void eng_dn_cb(lv_event_t *e) {
  int max_pages = (ENG_COUNT + ENG_PER_PAGE - 1) / ENG_PER_PAGE;
  if (eng_page < max_pages - 1) { eng_page++; refresh_eng_page(); }
}

void refresh_eng_page() {
  int max_pages = (ENG_COUNT + ENG_PER_PAGE - 1) / ENG_PER_PAGE;
  char tbuf[48];
  snprintf(tbuf, sizeof(tbuf), "Engineering   %d/%d", eng_page + 1, max_pages);
  if (lblEngTitle) lv_label_set_text(lblEngTitle, tbuf);
  for (int s = 0; s < ENG_PER_PAGE; s++) {
    int idx = eng_page * ENG_PER_PAGE + s;
    if (idx < ENG_COUNT) {
      lv_label_set_text(lblEngEntry[s], ENGINEERING_PROFILES[idx].name);
      lv_obj_clear_flag(btnEngEntry[s], LV_OBJ_FLAG_HIDDEN);
    } else {
      lv_obj_add_flag(btnEngEntry[s], LV_OBJ_FLAG_HIDDEN);
    }
  }
}

static void build_scrEngineer() {
  scrEngineer = lv_obj_create(NULL);
  style_screen(scrEngineer);
  lv_obj_clear_flag(scrEngineer, LV_OBJ_FLAG_SCROLLABLE);
  add_back_button(scrEngineer, back_to_material_cb);

  lblEngTitle = lv_label_create(scrEngineer);
  lv_label_set_text(lblEngTitle, "Engineering");
  lv_obj_set_style_text_color(lblEngTitle, lv_color_hex(CLR_TXT), 0);
  lv_obj_set_style_text_font (lblEngTitle, &lv_font_inter_16, 0);
  lv_obj_align(lblEngTitle, LV_ALIGN_TOP_MID, 0, 8);

  lv_obj_t *line = lv_obj_create(scrEngineer);
  lv_obj_set_size(line, SCREEN_W - 20, 1);
  lv_obj_set_pos(line, 10, 38);
  lv_obj_set_style_bg_color(line, lv_color_hex(CLR_BORDER), 0);
  lv_obj_set_style_border_width(line, 0, 0);
  lv_obj_clear_flag(line, LV_OBJ_FLAG_CLICKABLE | LV_OBJ_FLAG_SCROLLABLE);

  for (int i = 0; i < ENG_PER_PAGE; i++) {
    btnEngEntry[i] = make_themed_btn(scrEngineer, "",
                                     5, 50 + i * 60, 235, 56,
                                     eng_entry_cb, (void *)(intptr_t)i,
                                     ROLE_PRIMARY);
    lblEngEntry[i] = lv_obj_get_child(btnEngEntry[i], 0);
  }

  make_themed_btn(scrEngineer, LV_SYMBOL_UP,   245,  50, 70, 87,
                  eng_up_cb, NULL, ROLE_NEUTRAL);
  make_themed_btn(scrEngineer, LV_SYMBOL_DOWN, 245, 143, 70, 87,
                  eng_dn_cb, NULL, ROLE_NEUTRAL);
}

// ══════════════════════════════════════════════════════════════════
//   SECTION 24a — CUSTOM LIST (saved profiles)
//   The Custom category opens here. Lists all NVS-stored custom profiles,
//   3 per page, with arrow-nav. [+ New] opens the builder; tapping a
//   saved entry opens its detail screen (Select / Delete).
// ══════════════════════════════════════════════════════════════════
static void cust_entry_cb(lv_event_t *e) {
  int slot = (int)(intptr_t)lv_event_get_user_data(e);
  int idx = custom_list_page * 3 + slot;
  if (idx < 0 || idx >= saved_custom_count) return;
  show_scrCustomDetail(idx);
}
static void cust_up_cb(lv_event_t *e) {
  if (custom_list_page > 0) { custom_list_page--; refresh_custom_list(); }
}
static void cust_dn_cb(lv_event_t *e) {
  int max_pages = (saved_custom_count + 2) / 3;
  if (max_pages < 1) max_pages = 1;
  if (custom_list_page < max_pages - 1) { custom_list_page++; refresh_custom_list(); }
}
static void cust_new_cb(lv_event_t *e) {
  builder_step_count  = 0;
  builder_page        = 0;
  builder_editing_idx = -1;     // brand-new profile
  show_scrBuilder();
}

void refresh_custom_list() {
  if (!lblCustomTitle) return;
  int max_pages = (saved_custom_count + 2) / 3;
  if (max_pages < 1) max_pages = 1;
  char tbuf[48];
  snprintf(tbuf, sizeof(tbuf),
           "Custom Profiles   %d/%d",
           custom_list_page + 1, max_pages);
  lv_label_set_text(lblCustomTitle, tbuf);

  for (int s = 0; s < 3; s++) {
    int idx = custom_list_page * 3 + s;
    if (idx < saved_custom_count) {
      char row[48];
      snprintf(row, sizeof(row), "%s  (%d step%s)",
               saved_customs[idx].name, saved_customs[idx].step_count,
               saved_customs[idx].step_count == 1 ? "" : "s");
      lv_label_set_text(lblCustomEntry[s], row);
      lv_obj_clear_flag(btnCustomEntry[s], LV_OBJ_FLAG_HIDDEN);
    } else {
      lv_obj_add_flag(btnCustomEntry[s], LV_OBJ_FLAG_HIDDEN);
    }
  }
}

static void build_scrCustom() {
  scrCustom = lv_obj_create(NULL);
  style_screen(scrCustom);
  lv_obj_clear_flag(scrCustom, LV_OBJ_FLAG_SCROLLABLE);
  add_back_button(scrCustom, back_to_material_cb);

  lblCustomTitle = lv_label_create(scrCustom);
  lv_label_set_text(lblCustomTitle, "Custom Profiles");
  lv_obj_set_style_text_color(lblCustomTitle, lv_color_hex(CLR_TXT), 0);
  lv_obj_set_style_text_font (lblCustomTitle, &lv_font_inter_16, 0);
  lv_obj_align(lblCustomTitle, LV_ALIGN_TOP_MID, 0, 8);

  lv_obj_t *line = lv_obj_create(scrCustom);
  lv_obj_set_size(line, SCREEN_W - 20, 1);
  lv_obj_set_pos(line, 10, 38);
  lv_obj_set_style_bg_color(line, lv_color_hex(CLR_BORDER), 0);
  lv_obj_set_style_border_width(line, 0, 0);
  lv_obj_clear_flag(line, LV_OBJ_FLAG_CLICKABLE | LV_OBJ_FLAG_SCROLLABLE);

  for (int i = 0; i < 3; i++) {
    btnCustomEntry[i] = make_themed_btn(scrCustom, "",
                                        5, 46 + i * 52, 235, 48,
                                        cust_entry_cb, (void *)(intptr_t)i,
                                        ROLE_AMBER);
    lblCustomEntry[i] = lv_obj_get_child(btnCustomEntry[i], 0);
  }

  make_themed_btn(scrCustom, LV_SYMBOL_UP,   245,  46, 70, 74,
                  cust_up_cb, NULL, ROLE_NEUTRAL);
  make_themed_btn(scrCustom, LV_SYMBOL_DOWN, 245, 124, 70, 74,
                  cust_dn_cb, NULL, ROLE_NEUTRAL);

  make_themed_btn(scrCustom, LV_SYMBOL_PLUS "  New Profile",
                  5, 205, 310, 32,
                  cust_new_cb, NULL, ROLE_SUCCESS);
}

// ══════════════════════════════════════════════════════════════════
//   SECTION 24b — CUSTOM DETAIL (select / delete a saved profile)
// ══════════════════════════════════════════════════════════════════
static void detail_select_cb(lv_event_t *e) {
  if (custom_detail_idx < 0 || custom_detail_idx >= saved_custom_count) return;
  strncpy(selected_profile_name, saved_customs[custom_detail_idx].name,
          PROFILE_NAME_LEN - 1);
  selected_profile_name[PROFILE_NAME_LEN - 1] = 0;
  profile_is_selected = true;
  selected_custom_idx = custom_detail_idx;
  set_profile_button_label(selected_profile_name);
  refresh_profile_preview();
  show_scrMain();
}
static void detail_really_delete_cb(lv_event_t *e) {
  if (custom_detail_idx < 0 || custom_detail_idx >= saved_custom_count) return;
  // If the about-to-delete profile is currently selected, clear selection.
  if (selected_custom_idx == custom_detail_idx) {
    profile_is_selected = false;
    selected_custom_idx = -1;
    selected_profile_name[0] = 0;
    set_profile_button_label("Select Profile");
  } else if (selected_custom_idx > custom_detail_idx) {
    selected_custom_idx--;
  }
  deleteSavedCustom(custom_detail_idx);
  custom_detail_idx = -1;
  custom_list_page = 0;
  refresh_profile_preview();
  show_scrCustom();
}
static void detail_delete_cb(lv_event_t *e) {
  ui_show_messagebox("Delete profile?",
                     "This saved custom profile will be permanently removed.",
                     "Delete", "Cancel", detail_really_delete_cb);
}
static void detail_back_cb(lv_event_t *e) { show_scrCustom(); }
static void detail_rename_cb(lv_event_t *e) {
  if (custom_detail_idx < 0 || custom_detail_idx >= saved_custom_count) return;
  rename_target_idx   = custom_detail_idx;
  rename_save_builder = false;
  show_scrRename();
}
static void detail_edit_cb(lv_event_t *e) {
  if (custom_detail_idx < 0 || custom_detail_idx >= saved_custom_count) return;
  SavedCustom &sc = saved_customs[custom_detail_idx];
  builder_step_count = sc.step_count;
  for (int i = 0; i < sc.step_count; i++) builder_steps[i] = sc.steps[i];
  builder_editing_idx = custom_detail_idx;
  builder_page        = 0;
  show_scrBuilder();
}

static void build_scrCustomDetail() {
  scrCustomDetail = lv_obj_create(NULL);
  style_screen(scrCustomDetail);
  lv_obj_clear_flag(scrCustomDetail, LV_OBJ_FLAG_SCROLLABLE);
  add_back_button(scrCustomDetail, detail_back_cb);

  lblDetailTitle = lv_label_create(scrCustomDetail);
  lv_label_set_text(lblDetailTitle, "Custom");
  lv_obj_set_style_text_color(lblDetailTitle, lv_color_hex(CLR_TXT), 0);
  lv_obj_set_style_text_font (lblDetailTitle, &lv_font_inter_16, 0);
  lv_obj_align(lblDetailTitle, LV_ALIGN_TOP_MID, 0, 8);

  lv_obj_t *line = lv_obj_create(scrCustomDetail);
  lv_obj_set_size(line, SCREEN_W - 20, 1);
  lv_obj_set_pos(line, 10, 38);
  lv_obj_set_style_bg_color(line, lv_color_hex(CLR_BORDER), 0);
  lv_obj_set_style_border_width(line, 0, 0);
  lv_obj_clear_flag(line, LV_OBJ_FLAG_CLICKABLE | LV_OBJ_FLAG_SCROLLABLE);

  lv_obj_t *panel = lv_obj_create(scrCustomDetail);
  lv_obj_set_size(panel, 310, 120);
  lv_obj_set_pos(panel, 5, 44);
  lv_obj_set_style_bg_color    (panel, lv_color_hex(CLR_PANEL),  0);
  lv_obj_set_style_border_color(panel, lv_color_hex(CLR_BORDER), 0);
  lv_obj_set_style_border_width(panel, 1, 0);
  lv_obj_set_style_radius      (panel, 6, 0);
  lv_obj_set_style_pad_all     (panel, 6, 0);
  lv_obj_clear_flag(panel, LV_OBJ_FLAG_SCROLLABLE);

  lblDetailBody = lv_label_create(panel);
  lv_label_set_text(lblDetailBody, "");
  lv_label_set_long_mode(lblDetailBody, LV_LABEL_LONG_WRAP);
  lv_obj_set_width(lblDetailBody, 296);
  lv_obj_set_style_text_color(lblDetailBody, lv_color_hex(CLR_TXT), 0);
  lv_obj_set_style_text_font (lblDetailBody, &lv_font_inter_14, 0);

  // 4 buttons across: Select / Edit / Rename / Delete
  make_themed_btn(scrCustomDetail, "Select",   5, 170, 72, 60,
                  detail_select_cb, NULL, ROLE_SUCCESS);
  make_themed_btn(scrCustomDetail, "Edit",    82, 170, 72, 60,
                  detail_edit_cb,   NULL, ROLE_PRIMARY);
  make_themed_btn(scrCustomDetail, "Rename", 159, 170, 72, 60,
                  detail_rename_cb, NULL, ROLE_PRIMARY);
  make_themed_btn(scrCustomDetail, "Delete", 236, 170, 72, 60,
                  detail_delete_cb, NULL, ROLE_DANGER);
}

void show_scrCustomDetail(int idx) {
  if (idx < 0 || idx >= saved_custom_count) return;
  custom_detail_idx = idx;
  if (lblDetailTitle) lv_label_set_text(lblDetailTitle, saved_customs[idx].name);

  // Build body text: list every step
  char buf[512]; buf[0] = 0;
  for (int i = 0; i < saved_customs[idx].step_count; i++) {
    const ProfileStep &st = saved_customs[idx].steps[i];
    char line[96];
    if (st.is_ramp) {
      snprintf(line, sizeof(line),
               "%d.  RAMP %d\xC2\xB0 @ %.1f\xC2\xB0/min  hold %lum\n",
               i + 1, (int)roundf(st.target),
               st.rate_per_sec * 60.0f, st.hold_sec / 60UL);
    } else {
      snprintf(line, sizeof(line),
               "%d.  SET  %d\xC2\xB0  hold %lum\n",
               i + 1, (int)roundf(st.target), st.hold_sec / 60UL);
    }
    strncat(buf, line, sizeof(buf) - strlen(buf) - 1);
  }
  if (lblDetailBody) lv_label_set_text(lblDetailBody, buf);
  lv_scr_load(scrCustomDetail);
}

// ══════════════════════════════════════════════════════════════════
//   SECTION 24c — BUILDER (compose a new custom profile before saving)
// ══════════════════════════════════════════════════════════════════
static void builder_up_cb(lv_event_t *e) {
  if (builder_page > 0) { builder_page--; refresh_builder_page(); }
}
static void builder_dn_cb(lv_event_t *e) {
  int max_pages = (builder_step_count + BUILDER_PER_PAGE - 1) / BUILDER_PER_PAGE;
  if (max_pages < 1) max_pages = 1;
  if (builder_page < max_pages - 1) { builder_page++; refresh_builder_page(); }
}
static void builder_add_cb(lv_event_t *e) {
  if (builder_step_count >= PROFILE_MAX_STEPS) {
    ui_show_alert("Full", "This profile is full (16 steps max).");
    return;
  }
  editing_step_idx = -1;   // guarantee ADD (not EDIT) mode
  show_scrAddType();
}
static void builder_clear_cb(lv_event_t *e) {
  builder_step_count = 0;
  builder_page = 0;
  refresh_builder_page();
}
// Save behavior branches on whether we're editing an existing profile:
//   • editing  → write steps into the same slot, keep the existing name,
//                jump straight to that profile's detail screen.
//   • new      → route through the rename screen so the user names the
//                profile (auto-pre-filled with "Custom Profile N").
static void builder_save_cb(lv_event_t *e) {
  if (builder_step_count == 0) {
    ui_show_alert("Empty", "Add at least one step before saving.");
    return;
  }

  if (builder_editing_idx >= 0 && builder_editing_idx < saved_custom_count) {
    int idx = builder_editing_idx;
    saved_customs[idx].step_count = builder_step_count;
    for (int i = 0; i < builder_step_count; i++)
      saved_customs[idx].steps[i] = builder_steps[i];
    saveCustomProfiles();
    if (selected_custom_idx == idx) refresh_profile_preview();

    builder_step_count  = 0;
    builder_editing_idx = -1;
    builder_page        = 0;
    show_scrCustomDetail(idx);      // ← return to the edited profile's page
    return;
  }

  // New profile → name it via the rename screen.
  rename_save_builder = true;
  rename_target_idx   = -1;
  generate_next_custom_name(rename_default_name, sizeof(rename_default_name));
  show_scrRename();
}
static void builder_cancel_cb(lv_event_t *e) {
  builder_step_count  = 0;
  builder_page        = 0;
  builder_editing_idx = -1;
  show_scrCustom();
}

void refresh_builder_page() {
  if (!lblBuilderPage) return;
  int max_pages = (builder_step_count + BUILDER_PER_PAGE - 1) / BUILDER_PER_PAGE;
  if (max_pages < 1) max_pages = 1;
  if (builder_page >= max_pages) builder_page = max_pages - 1;
  if (builder_page < 0) builder_page = 0;

  char pbuf[32];
  snprintf(pbuf, sizeof(pbuf), "%d/%d   %d step%s",
           builder_page + 1, max_pages, builder_step_count,
           builder_step_count == 1 ? "" : "s");
  lv_label_set_text(lblBuilderPage, pbuf);

  if (builder_step_count == 0) {
    if (lblBuilderEmpty) lv_obj_clear_flag(lblBuilderEmpty, LV_OBJ_FLAG_HIDDEN);
    for (int i = 0; i < BUILDER_PER_PAGE; i++) {
      if (btnBuilderEntry[i]) lv_obj_add_flag(btnBuilderEntry[i], LV_OBJ_FLAG_HIDDEN);
    }
    return;
  }
  if (lblBuilderEmpty) lv_obj_add_flag(lblBuilderEmpty, LV_OBJ_FLAG_HIDDEN);

  int start = builder_page * BUILDER_PER_PAGE;
  int end   = start + BUILDER_PER_PAGE;
  if (end > builder_step_count) end = builder_step_count;

  for (int slot = 0; slot < BUILDER_PER_PAGE; slot++) {
    int idx = start + slot;
    if (idx < end) {
      const ProfileStep &st = builder_steps[idx];
      char line[96];
      if (st.is_ramp) {
        snprintf(line, sizeof(line),
                 "%d.  RAMP %d\xC2\xB0 @ %.1f\xC2\xB0/min  hold %lum",
                 idx + 1, (int)roundf(st.target),
                 st.rate_per_sec * 60.0f,
                 st.hold_sec / 60UL);
      } else {
        snprintf(line, sizeof(line),
                 "%d.  SET  %d\xC2\xB0  hold %lum",
                 idx + 1, (int)roundf(st.target),
                 st.hold_sec / 60UL);
      }
      lv_label_set_text(lblBuilderEntry[slot], line);
      lv_obj_clear_flag(btnBuilderEntry[slot], LV_OBJ_FLAG_HIDDEN);
    } else {
      lv_obj_add_flag(btnBuilderEntry[slot], LV_OBJ_FLAG_HIDDEN);
    }
  }
}

// Convert a float to the shortest sensible decimal representation for the
// keypad's entry buffer. Whole numbers render as "150"; non-whole as "2.5".
static void format_editable_value(char *out, size_t n, float v) {
  if (fabsf(v - roundf(v)) < 0.005f) {
    snprintf(out, n, "%d", (int)roundf(v));
  } else {
    snprintf(out, n, "%.2f", v);
  }
}

// Fired when the user actually confirms the "Edit step?" prompt — pre-loads
// add_tmp_values from the existing step and drops into the keypad at field 0.
static void edit_step_begin_cb(lv_event_t *e) {
  int idx = editing_step_idx;
  if (idx < 0 || idx >= builder_step_count) return;
  const ProfileStep &s = builder_steps[idx];
  add_kind      = s.is_ramp ? ADD_RAMP : ADD_SET;
  add_field_idx = 0;
  if (s.is_ramp) {
    add_tmp_values[0] = s.target;
    add_tmp_values[1] = s.rate_per_sec * 60.0f;
    add_tmp_values[2] = (float)s.hold_sec / 60.0f;
  } else {
    add_tmp_values[0] = s.target;
    add_tmp_values[1] = (float)s.hold_sec / 60.0f;
    add_tmp_values[2] = 0.0f;
  }
  // Pre-fill the keypad with the target field's current value.
  format_editable_value(keypad_buf, sizeof(keypad_buf), add_tmp_values[0]);
  lv_label_set_text(lblKeypadPrompt,
                    s.is_ramp ? "RAMP Target (\xC2\xB0""C)"
                              : "SET Target (\xC2\xB0""C)");
  lv_label_set_text(lblKeypadEntry, keypad_buf);
  lv_scr_load(scrKeypad);
}

// Actually remove the selected step and refresh the builder.
static void delete_step_confirmed_cb(lv_event_t *e) {
  int idx = editing_step_idx;
  if (idx < 0 || idx >= builder_step_count) { editing_step_idx = -1; return; }
  for (int i = idx; i < builder_step_count - 1; i++) {
    builder_steps[i] = builder_steps[i + 1];
  }
  builder_step_count--;
  editing_step_idx = -1;
  int max_pages = (builder_step_count + BUILDER_PER_PAGE - 1) / BUILDER_PER_PAGE;
  if (max_pages < 1) max_pages = 1;
  if (builder_page >= max_pages) builder_page = max_pages - 1;
  show_scrBuilder();
}

// Second-chance confirmation before destroying a step.
static void delete_step_prompt_cb(lv_event_t *e) {
  ui_show_messagebox("Delete step?",
                     "This step will be removed from the profile.",
                     "Delete", "Cancel",
                     delete_step_confirmed_cb);
}

// Three-button step-action dialog. Uses the existing msgbox shell directly
// because ui_show_messagebox only supports two buttons.
static void show_step_action_dialog() {
  lv_obj_t *box = make_msgbox_shell(CLR_AMBER);
  lv_obj_set_size(box, 300, 190);
  lv_obj_center(box);

  lv_obj_t *t = lv_label_create(box);
  lv_label_set_text(t, "Step action");
  lv_obj_set_style_text_color(t, lv_color_hex(CLR_AMBER), 0);
  lv_obj_set_style_text_font(t, &lv_font_inter_16, 0);
  lv_obj_align(t, LV_ALIGN_TOP_MID, 0, 0);

  lv_obj_t *b = lv_label_create(box);
  lv_label_set_text(b, "Edit this step or remove it from the profile?");
  lv_label_set_long_mode(b, LV_LABEL_LONG_WRAP);
  lv_obj_set_width(b, 270);
  lv_obj_set_style_text_color(b, lv_color_hex(CLR_TXT), 0);
  lv_obj_set_style_text_font(b, &lv_font_inter_14, 0);
  lv_obj_align(b, LV_ALIGN_TOP_MID, 0, 28);

  // Three actions — msgbox_confirm_cb kills the box and fires the callback
  // passed as user_data. msgbox_close_cb simply closes.
  make_themed_btn(box, "Edit",     5, 120,  88, 40,
                  msgbox_confirm_cb, (void *)edit_step_begin_cb, ROLE_PRIMARY);
  make_themed_btn(box, "Delete",  97, 120,  88, 40,
                  msgbox_confirm_cb, (void *)delete_step_prompt_cb, ROLE_DANGER);
  make_themed_btn(box, "Cancel", 189, 120,  92, 40,
                  msgbox_close_cb, NULL, ROLE_NEUTRAL);
}

// Each builder row carries its PAGE-RELATIVE slot (0..BUILDER_PER_PAGE-1)
// as user_data — we compute the absolute step index at click time from
// builder_page. This avoids having to rebind handlers on every page turn.
void builder_entry_cb(lv_event_t *e) {
  int slot = (int)(intptr_t)lv_event_get_user_data(e);
  int idx  = builder_page * BUILDER_PER_PAGE + slot;
  if (idx < 0 || idx >= builder_step_count) return;
  editing_step_idx = idx;
  show_step_action_dialog();
}

static void build_scrBuilder() {
  scrBuilder = lv_obj_create(NULL);
  style_screen(scrBuilder);
  lv_obj_clear_flag(scrBuilder, LV_OBJ_FLAG_SCROLLABLE);
  add_back_button(scrBuilder, builder_cancel_cb);

  lblBuilderTitle = lv_label_create(scrBuilder);
  lv_label_set_text(lblBuilderTitle, "New Custom Profile");
  lv_obj_set_style_text_color(lblBuilderTitle, lv_color_hex(CLR_TXT), 0);
  lv_obj_set_style_text_font (lblBuilderTitle, &lv_font_inter_16, 0);
  lv_obj_align(lblBuilderTitle, LV_ALIGN_TOP_MID, 0, 8);

  lblBuilderPage = lv_label_create(scrBuilder);
  lv_label_set_text(lblBuilderPage, "1/1  0 steps");
  lv_obj_set_style_text_color(lblBuilderPage, lv_color_hex(CLR_TXT_DIM), 0);
  lv_obj_set_style_text_font (lblBuilderPage, &lv_font_inter_14, 0);
  lv_obj_align(lblBuilderPage, LV_ALIGN_TOP_RIGHT, -6, 12);

  lv_obj_t *line = lv_obj_create(scrBuilder);
  lv_obj_set_size(line, SCREEN_W - 20, 1);
  lv_obj_set_pos(line, 10, 38);
  lv_obj_set_style_bg_color(line, lv_color_hex(CLR_BORDER), 0);
  lv_obj_set_style_border_width(line, 0, 0);
  lv_obj_clear_flag(line, LV_OBJ_FLAG_CLICKABLE | LV_OBJ_FLAG_SCROLLABLE);

  lv_obj_t *panel = lv_obj_create(scrBuilder);
  lv_obj_set_size(panel, 240, 130);
  lv_obj_set_pos(panel, 5, 44);
  lv_obj_set_style_bg_color    (panel, lv_color_hex(CLR_PANEL),  0);
  lv_obj_set_style_border_color(panel, lv_color_hex(CLR_BORDER), 0);
  lv_obj_set_style_border_width(panel, 1, 0);
  lv_obj_set_style_radius      (panel, 6, 0);
  lv_obj_set_style_pad_all     (panel, 4, 0);
  lv_obj_clear_flag(panel, LV_OBJ_FLAG_SCROLLABLE);

  // Empty-state placeholder — shown only when builder_step_count == 0.
  lblBuilderEmpty = lv_label_create(panel);
  lv_label_set_text(lblBuilderEmpty, "(Press + to add a step)");
  lv_obj_set_style_text_color(lblBuilderEmpty, lv_color_hex(CLR_TXT_DIM), 0);
  lv_obj_set_style_text_font (lblBuilderEmpty, &lv_font_inter_14, 0);
  lv_obj_center(lblBuilderEmpty);

  // One clickable row per visible step. Panel is 240×130 with pad_all=4,
  // so usable is 232×122. Four buttons at 28 tall + 2 px gaps = 118 → fits.
  extern void builder_entry_cb(lv_event_t *e);
  for (int i = 0; i < BUILDER_PER_PAGE; i++) {
    btnBuilderEntry[i] = lv_btn_create(panel);
    lv_obj_set_size(btnBuilderEntry[i], 228, 28);
    lv_obj_set_pos(btnBuilderEntry[i], 0, i * 30);
    lv_obj_set_style_bg_color    (btnBuilderEntry[i], lv_color_hex(CLR_PANEL2), 0);
    lv_obj_set_style_bg_color    (btnBuilderEntry[i], lv_color_hex(CLR_ACCENT_D), LV_STATE_PRESSED);
    lv_obj_set_style_border_color(btnBuilderEntry[i], lv_color_hex(CLR_BORDER), 0);
    lv_obj_set_style_border_width(btnBuilderEntry[i], 1, 0);
    lv_obj_set_style_radius      (btnBuilderEntry[i], 4, 0);
    lv_obj_set_style_shadow_width(btnBuilderEntry[i], 0, 0);
    lv_obj_set_style_text_color  (btnBuilderEntry[i], lv_color_hex(CLR_TXT), 0);
    lv_obj_add_event_cb(btnBuilderEntry[i], builder_entry_cb,
                        LV_EVENT_CLICKED, (void *)(intptr_t)i);
    lblBuilderEntry[i] = lv_label_create(btnBuilderEntry[i]);
    lv_label_set_text(lblBuilderEntry[i], "");
    lv_obj_set_style_text_font(lblBuilderEntry[i], &lv_font_inter_14, 0);
    lv_obj_align(lblBuilderEntry[i], LV_ALIGN_LEFT_MID, 6, 0);
    lv_obj_add_flag(btnBuilderEntry[i], LV_OBJ_FLAG_HIDDEN);
  }

  make_themed_btn(scrBuilder, LV_SYMBOL_UP,   250,  44, 65, 60,
                  builder_up_cb, NULL, ROLE_NEUTRAL);
  make_themed_btn(scrBuilder, LV_SYMBOL_DOWN, 250, 114, 65, 60,
                  builder_dn_cb, NULL, ROLE_NEUTRAL);

  make_themed_btn(scrBuilder, LV_SYMBOL_PLUS,    5, 180, 75, 54,
                  builder_add_cb,    NULL, ROLE_SUCCESS);
  make_themed_btn(scrBuilder, "Clear",          85, 180, 110, 54,
                  builder_clear_cb,  NULL, ROLE_DANGER);
  make_themed_btn(scrBuilder, "Save",          200, 180, 115, 54,
                  builder_save_cb,   NULL, ROLE_PRIMARY);
}

// ══════════════════════════════════════════════════════════════════
//   SECTION 25 — ADD-TYPE SCREEN (RAMP / SET / Cancel)
// ══════════════════════════════════════════════════════════════════
static void addtype_ramp_cb(lv_event_t *e) {
  add_kind = ADD_RAMP;
  add_field_idx = 0;
  for (int i = 0; i < 3; i++) add_tmp_values[i] = 0.0f;
  show_scrKeypad("RAMP Target (\xC2\xB0""C)");
}
static void addtype_set_cb(lv_event_t *e) {
  add_kind = ADD_SET;
  add_field_idx = 0;
  for (int i = 0; i < 3; i++) add_tmp_values[i] = 0.0f;
  show_scrKeypad("SET Target (\xC2\xB0""C)");
}
static void addtype_cancel_cb(lv_event_t *e) { show_scrBuilder(); }

static void build_scrAddType() {
  scrAddType = lv_obj_create(NULL);
  style_screen(scrAddType);
  lv_obj_clear_flag(scrAddType, LV_OBJ_FLAG_SCROLLABLE);
  add_back_button(scrAddType, addtype_cancel_cb);
  add_title(scrAddType, "Add Step");

  make_themed_btn(scrAddType, "RAMP", 15,  60, 290, 85, addtype_ramp_cb, NULL, ROLE_PRIMARY);
  make_themed_btn(scrAddType, "SET",  15, 150, 290, 85, addtype_set_cb,  NULL, ROLE_PRIMARY);
}

// ══════════════════════════════════════════════════════════════════
//   SECTION 26 — NUMERIC KEYPAD
// ══════════════════════════════════════════════════════════════════
static void keypad_append(char c) {
  int len = strlen(keypad_buf);
  if (len < (int)sizeof(keypad_buf) - 1) {
    keypad_buf[len] = c;
    keypad_buf[len + 1] = 0;
    lv_label_set_text(lblKeypadEntry, keypad_buf);
  }
}
static void keypad_digit_cb(lv_event_t *e) {
  int d = (int)(intptr_t)lv_event_get_user_data(e);
  keypad_append('0' + d);
}
static void keypad_dot_cb(lv_event_t *e) {
  if (strchr(keypad_buf, '.')) return;
  if (keypad_buf[0] == 0) keypad_append('0');
  keypad_append('.');
}
static void keypad_back_cb(lv_event_t *e) {
  int len = strlen(keypad_buf);
  if (len > 0) {
    keypad_buf[len - 1] = 0;
    lv_label_set_text(lblKeypadEntry, keypad_buf[0] ? keypad_buf : "0");
  }
}
static void keypad_clear_cb(lv_event_t *e) {
  keypad_buf[0] = 0;
  lv_label_set_text(lblKeypadEntry, "0");
}
static void keypad_cancel_cb(lv_event_t *e) {
  add_kind         = ADD_NONE;
  editing_step_idx = -1;
  show_scrBuilder();
}
static void keypad_ok_cb(lv_event_t *e) {
  commit_keypad_value();
}

void show_scrKeypad(const char *prompt) {
  keypad_buf[0] = 0;
  lv_label_set_text(lblKeypadPrompt, prompt);
  lv_label_set_text(lblKeypadEntry, "0");
  lv_scr_load(scrKeypad);
}

// After OK: stash value, advance to next field, or finalize. When editing
// an existing step the next field is pre-filled with its stored value;
// when adding a new step we start blank.
void commit_keypad_value() {
  float v = keypad_buf[0] ? atof(keypad_buf) : 0.0f;
  add_tmp_values[add_field_idx] = v;
  add_field_idx++;

  auto prep_field = [](const char *prompt) {
    if (editing_step_idx >= 0) {
      format_editable_value(keypad_buf, sizeof(keypad_buf),
                            add_tmp_values[add_field_idx]);
      lv_label_set_text(lblKeypadEntry, keypad_buf);
    } else {
      keypad_buf[0] = 0;
      lv_label_set_text(lblKeypadEntry, "0");
    }
    lv_label_set_text(lblKeypadPrompt, prompt);
  };

  if (add_kind == ADD_RAMP && add_field_idx < 3) {
    prep_field(add_field_idx == 1 ? "RAMP Rate (\xC2\xB0""C/min)"
                                  : "RAMP Hold Duration (min)");
    return;
  }
  if (add_kind == ADD_SET && add_field_idx < 2) {
    prep_field("SET Hold Duration (min)");
    return;
  }
  finalize_add_step();
}

void finalize_add_step() {
  // Where the resulting step goes — either overwriting an edited row or
  // appended at the end. The "previous" step for the rate-cap direction
  // check always comes from index (target_idx - 1), ambient for the first.
  const bool editing   = (editing_step_idx >= 0 && editing_step_idx < builder_step_count);
  const int  target_idx = editing ? editing_step_idx : builder_step_count;

  auto bail = [](const char *title, const char *body) {
    ui_show_alert(title, body);
    add_kind         = ADD_NONE;
    editing_step_idx = -1;
    show_scrBuilder();
  };

  if (add_kind == ADD_RAMP) {
    float tgt = add_tmp_values[0], rate = add_tmp_values[1], hold = add_tmp_values[2];
    if (tgt < 20.0f || tgt > 200.0f) { bail("Invalid", "Target must be 20-200 \xC2\xB0""C."); return; }
    if (rate <= 0.0f)                 { bail("Invalid", "Rate must be > 0 \xC2\xB0""C/min."); return; }
    if (hold < 0.0f)                  { bail("Invalid", "Hold must be \xE2\x89\xA5 0 min.");  return; }

    float prev_target = (target_idx > 0) ? builder_steps[target_idx - 1].target : 20.0f;
    if (tgt > prev_target && rate > MAX_HEATING_RATE_C_PER_MIN) {
      char buf[128];
      snprintf(buf, sizeof(buf),
               "Heating rate capped at %.2f \xC2\xB0""C/min. "
               "Entered %.2f is too fast.",
               MAX_HEATING_RATE_C_PER_MIN, rate);
      bail("Rate too high", buf); return;
    }
    if (tgt < prev_target && rate > MAX_COOLING_RATE_C_PER_MIN) {
      char buf[128];
      snprintf(buf, sizeof(buf),
               "Cooling rate capped at %.2f \xC2\xB0""C/min. "
               "Entered %.2f is too fast.",
               MAX_COOLING_RATE_C_PER_MIN, rate);
      bail("Rate too high", buf); return;
    }

    builder_steps[target_idx].is_ramp      = true;
    builder_steps[target_idx].target       = tgt;
    builder_steps[target_idx].rate_per_sec = rate / 60.0f;
    builder_steps[target_idx].hold_sec     = (unsigned long)(hold * 60.0f);
    if (!editing) builder_step_count++;
  } else if (add_kind == ADD_SET) {
    float tgt = add_tmp_values[0], hold = add_tmp_values[1];
    if (tgt < 20.0f || tgt > 200.0f) { bail("Invalid", "Target must be 20-200 \xC2\xB0""C."); return; }
    if (hold < 0.0f)                  { bail("Invalid", "Hold must be \xE2\x89\xA5 0 min.");  return; }
    builder_steps[target_idx].is_ramp      = false;
    builder_steps[target_idx].target       = tgt;
    builder_steps[target_idx].rate_per_sec = 0.0f;
    builder_steps[target_idx].hold_sec     = (unsigned long)(hold * 60.0f);
    if (!editing) builder_step_count++;
  }

  add_kind         = ADD_NONE;
  add_field_idx    = 0;
  editing_step_idx = -1;
  builder_page     = target_idx / BUILDER_PER_PAGE;
  show_scrBuilder();
}

static void build_scrKeypad() {
  scrKeypad = lv_obj_create(NULL);
  style_screen(scrKeypad);
  lv_obj_clear_flag(scrKeypad, LV_OBJ_FLAG_SCROLLABLE);
  add_back_button(scrKeypad, keypad_cancel_cb);

  lblKeypadPrompt = lv_label_create(scrKeypad);
  lv_label_set_text(lblKeypadPrompt, "Enter value");
  lv_obj_set_style_text_color(lblKeypadPrompt, lv_color_hex(CLR_ACCENT), 0);
  lv_obj_set_style_text_font (lblKeypadPrompt, &lv_font_inter_16, 0);
  lv_obj_align(lblKeypadPrompt, LV_ALIGN_TOP_MID, 15, 10);

  lv_obj_t *entry_panel = lv_obj_create(scrKeypad);
  lv_obj_set_size(entry_panel, 310, 36);
  lv_obj_set_pos(entry_panel, 5, 38);
  lv_obj_set_style_bg_color    (entry_panel, lv_color_hex(CLR_PANEL2), 0);
  lv_obj_set_style_border_color(entry_panel, lv_color_hex(CLR_BORDER), 0);
  lv_obj_set_style_border_width(entry_panel, 1, 0);
  lv_obj_set_style_radius      (entry_panel, 6, 0);
  lv_obj_set_style_pad_all     (entry_panel, 4, 0);
  lv_obj_clear_flag(entry_panel, LV_OBJ_FLAG_SCROLLABLE);

  lblKeypadEntry = lv_label_create(entry_panel);
  lv_label_set_text(lblKeypadEntry, "0");
  lv_obj_set_style_text_color(lblKeypadEntry, lv_color_hex(CLR_TXT), 0);
  lv_obj_set_style_text_font (lblKeypadEntry, &lv_font_inter_24, 0);
  lv_obj_align(lblKeypadEntry, LV_ALIGN_RIGHT_MID, -6, 0);

  struct { const char *t; int c; int r; lv_event_cb_t cb; int dig; BtnRole role; } pads[] = {
    {"7", 0, 0, keypad_digit_cb, 7, ROLE_NEUTRAL},
    {"8", 1, 0, keypad_digit_cb, 8, ROLE_NEUTRAL},
    {"9", 2, 0, keypad_digit_cb, 9, ROLE_NEUTRAL},
    {"4", 0, 1, keypad_digit_cb, 4, ROLE_NEUTRAL},
    {"5", 1, 1, keypad_digit_cb, 5, ROLE_NEUTRAL},
    {"6", 2, 1, keypad_digit_cb, 6, ROLE_NEUTRAL},
    {"1", 0, 2, keypad_digit_cb, 1, ROLE_NEUTRAL},
    {"2", 1, 2, keypad_digit_cb, 2, ROLE_NEUTRAL},
    {"3", 2, 2, keypad_digit_cb, 3, ROLE_NEUTRAL},
    {".", 0, 3, keypad_dot_cb,   0, ROLE_NEUTRAL},
    {"0", 1, 3, keypad_digit_cb, 0, ROLE_NEUTRAL},
    {LV_SYMBOL_BACKSPACE, 2, 3, keypad_back_cb, 0, ROLE_AMBER},
  };
  for (auto &p : pads) {
    int x = 5 + p.c * 60;
    int y = 82 + p.r * 38;
    make_themed_btn(scrKeypad, p.t, x, y, 56, 34,
                    p.cb,
                    (p.cb == keypad_digit_cb) ? (void *)(intptr_t)p.dig : NULL,
                    p.role);
  }

  make_themed_btn(scrKeypad, "CLR", 245,  82, 70, 68,
                  keypad_clear_cb, NULL, ROLE_AMBER);
  make_themed_btn(scrKeypad, "OK",  245, 156, 70, 80,
                  keypad_ok_cb,    NULL, ROLE_SUCCESS);
}

// ══════════════════════════════════════════════════════════════════
//   SECTION 26B — FULLSCREEN GRAPH
//   A second chart object mirrors the main chart; both write-helpers
//   (setup/teardown/actual/idle) push values to both so the view is
//   consistent regardless of which screen is loaded.
// ══════════════════════════════════════════════════════════════════
static void fullgraph_back_cb(lv_event_t *e) { show_scrMain(); }

static void build_scrFullGraph() {
  scrFullGraph = lv_obj_create(NULL);
  style_screen(scrFullGraph);
  lv_obj_clear_flag(scrFullGraph, LV_OBJ_FLAG_SCROLLABLE);
  add_back_button(scrFullGraph, fullgraph_back_cb);

  lblFullTitle = lv_label_create(scrFullGraph);
  lv_label_set_text(lblFullTitle, "60-minute history");
  lv_obj_set_style_text_color(lblFullTitle, lv_color_hex(CLR_TXT), 0);
  lv_obj_set_style_text_font (lblFullTitle, &lv_font_inter_16, 0);
  lv_obj_align(lblFullTitle, LV_ALIGN_TOP_MID, 0, 8);

  // Chart fills the width — Y labels are painted on TOP of the plot area
  // (so the draw area is preserved, not shrunk by a gutter).
  chartFull = lv_chart_create(scrFullGraph);
  lv_obj_set_size(chartFull, 310, 170);
  lv_obj_set_pos(chartFull, 5, 38);
  lv_chart_set_type(chartFull, LV_CHART_TYPE_LINE);
  lv_chart_set_point_count(chartFull, GRAPH_SAMPLES);
  lv_chart_set_range(chartFull, LV_CHART_AXIS_PRIMARY_Y, 20, 220);
  lv_chart_set_update_mode(chartFull, LV_CHART_UPDATE_MODE_SHIFT);
  lv_chart_set_div_line_count(chartFull, 6, 8);
  lv_obj_set_style_size(chartFull, 0, LV_PART_INDICATOR);
  lv_obj_set_style_bg_color    (chartFull, lv_color_hex(CLR_PANEL2),  0);
  lv_obj_set_style_border_color(chartFull, lv_color_hex(CLR_BORDER),  0);
  lv_obj_set_style_border_width(chartFull, 1, 0);
  lv_obj_set_style_line_color  (chartFull, lv_color_hex(CLR_GRID),    LV_PART_MAIN);
  lv_obj_set_style_line_width  (chartFull, 1,                         LV_PART_MAIN);
  lv_obj_set_style_pad_left    (chartFull, 4, 0);
  lv_obj_set_style_pad_right   (chartFull, 4, 0);
  lv_obj_set_style_pad_top     (chartFull, 2, 0);
  lv_obj_set_style_pad_bottom  (chartFull, 2, 0);
  lv_obj_set_style_line_width  (chartFull, 2, LV_PART_ITEMS);
  lv_obj_clear_flag(chartFull, LV_OBJ_FLAG_CLICKABLE);
  serSPFull   = lv_chart_add_series(chartFull, lv_color_hex(CLR_PLANNED), LV_CHART_AXIS_PRIMARY_Y);
  serTempFull = lv_chart_add_series(chartFull, lv_color_hex(CLR_ACTUAL),  LV_CHART_AXIS_PRIMARY_Y);

  // Y-axis labels painted OVER the plot area, hard-left. 6 equally spaced
  // ticks from 220 °C (top) down to 20 °C (bottom). The chart is at y=38..208.
  // Plot draw area (after pad_top=2 and pad_bottom=2) is roughly y=40..206.
  static const int Y_VALUES[FULL_Y_LABELS] = { 220, 180, 140, 100, 60, 20 };
  static const int Y_POSITIONS[FULL_Y_LABELS] = { 38, 72, 106, 139, 173, 197 };
  for (int i = 0; i < FULL_Y_LABELS; i++) {
    lblFullY[i] = lv_label_create(scrFullGraph);
    char buf[8];
    snprintf(buf, sizeof(buf), "%d", Y_VALUES[i]);
    lv_label_set_text(lblFullY[i], buf);
    lv_obj_set_style_text_color(lblFullY[i], lv_color_hex(CLR_TXT_DIM), 0);
    lv_obj_set_style_text_font (lblFullY[i], &lv_font_inter_12, 0);
    // Semi-transparent background tint so the digits stay readable over grid lines
    lv_obj_set_style_bg_color  (lblFullY[i], lv_color_hex(CLR_PANEL), 0);
    lv_obj_set_style_bg_opa    (lblFullY[i], LV_OPA_70, 0);
    lv_obj_set_style_pad_hor   (lblFullY[i], 2, 0);
    lv_obj_set_style_radius    (lblFullY[i], 2, 0);
    lv_obj_set_pos(lblFullY[i], 9, Y_POSITIONS[i]);
  }

  // Tiny °C unit indicator in the top-left corner of the plot area
  lv_obj_t *lblUnit = lv_label_create(scrFullGraph);
  lv_label_set_text(lblUnit, "\xC2\xB0""C");
  lv_obj_set_style_text_color(lblUnit, lv_color_hex(CLR_TXT_DIM), 0);
  lv_obj_set_style_text_font (lblUnit, &lv_font_inter_12, 0);
  lv_obj_set_style_bg_color  (lblUnit, lv_color_hex(CLR_PANEL), 0);
  lv_obj_set_style_bg_opa    (lblUnit, LV_OPA_70, 0);
  lv_obj_set_style_pad_hor   (lblUnit, 2, 0);
  lv_obj_set_style_radius    (lblUnit, 2, 0);
  // Inside the plot area, top-right corner — keeps the back button's
  // drop zone (x<60, y<34) completely clear.
  lv_obj_set_pos(lblUnit, 290, 42);

  // X-axis labels — created here with uniform styling; positions/texts are
  // assigned each time set_full_xaxis_* runs.
  for (int i = 0; i < FULL_X_MAX_LABELS; i++) {
    lblFullX[i] = lv_label_create(scrFullGraph);
    lv_label_set_text(lblFullX[i], "");
    lv_obj_set_style_text_color(lblFullX[i], lv_color_hex(CLR_TXT_DIM), 0);
    lv_obj_set_style_text_font (lblFullX[i], &lv_font_inter_12, 0);
    lv_obj_add_flag(lblFullX[i], LV_OBJ_FLAG_HIDDEN);
  }

  // Legend bottom of screen
  lv_obj_t *lp = lv_obj_create(scrFullGraph);
  lv_obj_set_size(lp, 10, 10); lv_obj_set_pos(lp, 10, 225);
  lv_obj_set_style_bg_color(lp, lv_color_hex(CLR_PLANNED), 0);
  lv_obj_set_style_border_width(lp, 0, 0); lv_obj_set_style_radius(lp, 1, 0);
  lv_obj_clear_flag(lp, LV_OBJ_FLAG_CLICKABLE | LV_OBJ_FLAG_SCROLLABLE);
  lv_obj_t *la = lv_obj_create(scrFullGraph);
  lv_obj_set_size(la, 10, 10); lv_obj_set_pos(la, 150, 225);
  lv_obj_set_style_bg_color(la, lv_color_hex(CLR_ACTUAL), 0);
  lv_obj_set_style_border_width(la, 0, 0); lv_obj_set_style_radius(la, 1, 0);
  lv_obj_clear_flag(la, LV_OBJ_FLAG_CLICKABLE | LV_OBJ_FLAG_SCROLLABLE);
  lv_obj_t *lpt = lv_label_create(scrFullGraph);
  lv_label_set_text(lpt, "planned");
  lv_obj_set_style_text_color(lpt, lv_color_hex(CLR_TXT_DIM), 0);
  lv_obj_set_style_text_font (lpt, &lv_font_inter_12, 0);
  lv_obj_set_pos(lpt, 25, 223);
  lv_obj_t *lat = lv_label_create(scrFullGraph);
  lv_label_set_text(lat, "actual");
  lv_obj_set_style_text_color(lat, lv_color_hex(CLR_TXT_DIM), 0);
  lv_obj_set_style_text_font (lat, &lv_font_inter_12, 0);
  lv_obj_set_pos(lat, 165, 223);
  lv_obj_t *lmin = lv_label_create(scrFullGraph);
  lv_label_set_text(lmin, "min");
  lv_obj_set_style_text_color(lmin, lv_color_hex(CLR_TXT_DIM), 0);
  lv_obj_set_style_text_font (lmin, &lv_font_inter_12, 0);
  lv_obj_align(lmin, LV_ALIGN_TOP_RIGHT, -4, 223);
}

// ══════════════════════════════════════════════════════════════════
//   SECTION 26C — PROFILE PREVIEW
//   On selection, draw the planned trajectory immediately (without
//   starting). When selection is cleared or profile ends, revert to
//   rolling history.
// ══════════════════════════════════════════════════════════════════
static int find_predef_household(const char *name) {
  for (int i = 0; i < HOUSEHOLD_COUNT; i++)
    if (!strcmp(HOUSEHOLD_PROFILES[i].name, name)) return i;
  return -1;
}
static int find_predef_eng(const char *name) {
  for (int i = 0; i < ENG_COUNT; i++)
    if (!strcmp(ENGINEERING_PROFILES[i].name, name)) return i;
  return -1;
}

void refresh_profile_preview() {
  if (profile_state > 0) return;  // running — live update owns the chart
  if (!profile_is_selected) { teardownProfileGraph(); return; }

  const ProfileStep *steps = NULL;
  int count = 0;
  if (selected_custom_idx >= 0 && selected_custom_idx < saved_custom_count) {
    steps = saved_customs[selected_custom_idx].steps;
    count = saved_customs[selected_custom_idx].step_count;
  } else {
    int i = find_predef_household(selected_profile_name);
    if (i >= 0) { steps = HOUSEHOLD_PROFILES[i].steps;    count = HOUSEHOLD_PROFILES[i].step_count; }
    else {
      i = find_predef_eng(selected_profile_name);
      if (i >= 0) { steps = ENGINEERING_PROFILES[i].steps; count = ENGINEERING_PROFILES[i].step_count; }
    }
  }
  if (!steps || count == 0) { teardownProfileGraph(); return; }
  computePlannedTrajectory(steps, count, current_temp);
  setupProfileGraph();
}

// ══════════════════════════════════════════════════════════════════
//   SECTION 26D — SETTINGS SCREEN
// ══════════════════════════════════════════════════════════════════
static void settings_back_cb(lv_event_t *e) { show_scrMain(); }
static void settings_cal_cb (lv_event_t *e) { show_scrCalibrate(); }

// -------- Restore Defaults: touch cal + plant model + PID gains ----------
static void restore_defaults_apply_cb(lv_event_t *e) {
  // Touch calibration → fallback values, mirrored into NVS.
  ts_min_x = 300; ts_max_x = 3800;
  ts_min_y = 300; ts_max_y = 3800;
  preferences.putShort("ts_minx", ts_min_x);
  preferences.putShort("ts_maxx", ts_max_x);
  preferences.putShort("ts_miny", ts_min_y);
  preferences.putShort("ts_maxy", ts_max_y);

  // Factory plant identification + PID gains.
  plant_K     = 0.043061f;
  plant_tau   = 0.0f;
  plant_theta = 165.5f;
  Kc          = 0.070512f;
  Ti          = 1317.38f;
  lambda_val  = 3.0f;
  preferences.putFloat("K",      plant_K);
  preferences.putFloat("tau",    plant_tau);
  preferences.putFloat("theta",  plant_theta);
  preferences.putFloat("Kc",     Kc);
  preferences.putFloat("Ti",     Ti);
  preferences.putFloat("lambda", lambda_val);

  Serial.println("\n[RESET] Defaults restored (touch cal + plant + PID).");
  ui_show_info("Restored", "Touch calibration and tuning reset to factory defaults.");
}

static void settings_restore_defaults_cb(lv_event_t *e) {
  ui_show_messagebox(
    "Restore Defaults?",
    "Touchscreen calibration and PID tuning will be reset to factory values. "
    "Saved profiles and WiFi credentials are kept.",
    "Restore", "Cancel",
    restore_defaults_apply_cb);
}

// -------- Factory Reset: wipe all NVS namespaces, reboot ------------------
// Two-layer confirmation: scary first dialog, "are you sure" second dialog,
// only the second's OK actually erases.
static void factory_reset_apply_cb(lv_event_t *e) {
  Serial.println("\n[RESET] *** FACTORY RESET *** wiping NVS and rebooting.");
  // Close our active "pid_data" handle, then nuke every namespace we own.
  preferences.end();
  Preferences p;
  p.begin("pid_data", false); p.clear(); p.end();
  p.begin("custom",   false); p.clear(); p.end();
  p.begin("wifi",     false); p.clear(); p.end();
  delay(300);
  ESP.restart();   // never returns
}
static void factory_reset_step2_cb(lv_event_t *e) {
  ui_show_messagebox(
    "Are you sure?",
    "This cannot be undone. The device will erase ALL settings and reboot.",
    "Erase All", "Cancel",
    factory_reset_apply_cb);
}
static void settings_factory_reset_cb(lv_event_t *e) {
  ui_show_messagebox(
    "Factory Reset?",
    "Erase ALL settings, custom profiles, calibration, tuning, and WiFi credentials?",
    "Continue", "Cancel",
    factory_reset_step2_cb);
}
// NOTE: auto-tune is deliberately no longer exposed in the UI. Factory-
// default plant identification is loaded at boot in setup(). If the plant
// ever needs to be retuned, the serial `TUNE` command still runs the full
// identification routine and overwrites the NVS values.

static void build_scrSettings() {
  scrSettings = lv_obj_create(NULL);
  style_screen(scrSettings);
  lv_obj_clear_flag(scrSettings, LV_OBJ_FLAG_SCROLLABLE);
  add_back_button(scrSettings, settings_back_cb);
  add_title(scrSettings, "Settings");

  // Four stacked actions on the left. Auto-tune lives on the serial
  // interface (`TUNE`) only.
  make_themed_btn(scrSettings, "Touchscreen Calibration",
                  5,  44, 205, 38, settings_cal_cb, NULL, ROLE_PRIMARY);
  make_themed_btn(scrSettings, "WiFi",
                  5,  86, 205, 38,
                  [](lv_event_t *e) { show_scrWifi(); },
                  NULL, ROLE_PRIMARY);
  make_themed_btn(scrSettings, "Restore Defaults",
                  5, 128, 205, 38, settings_restore_defaults_cb, NULL, ROLE_AMBER);
  make_themed_btn(scrSettings, "Factory Reset",
                  5, 170, 205, 38, settings_factory_reset_cb, NULL, ROLE_DANGER);

  // Right: QR code panel + caption directly under it
  lv_obj_t *qrPanel = lv_obj_create(scrSettings);
  lv_obj_set_size(qrPanel, 100, 100);
  lv_obj_set_pos(qrPanel, 215, 50);
  lv_obj_set_style_bg_color    (qrPanel, lv_color_hex(CLR_PANEL),  0);
  lv_obj_set_style_border_color(qrPanel, lv_color_hex(CLR_BORDER), 0);
  lv_obj_set_style_border_width(qrPanel, 1, 0);
  lv_obj_set_style_radius      (qrPanel, 6, 0);
  lv_obj_set_style_pad_all     (qrPanel, 5, 0);
  lv_obj_clear_flag(qrPanel, LV_OBJ_FLAG_SCROLLABLE | LV_OBJ_FLAG_CLICKABLE);

  lv_obj_t *qr = lv_qrcode_create(qrPanel, 88,
                                  lv_color_hex(0x000000),
                                  lv_color_hex(0xFFFFFF));
  static const char *QR_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ";
  lv_qrcode_update(qr, QR_URL, strlen(QR_URL));
  lv_obj_align(qr, LV_ALIGN_TOP_MID, 0, 0);

  // Caption: centered horizontally under the QR panel
  lv_obj_t *qrLbl = lv_label_create(scrSettings);
  lv_label_set_text(qrLbl, "More Info");
  lv_obj_set_style_text_color(qrLbl, lv_color_hex(CLR_TXT_DIM), 0);
  lv_obj_set_style_text_font (qrLbl, &lv_font_inter_14, 0);
  lv_obj_set_style_text_align(qrLbl, LV_TEXT_ALIGN_CENTER, 0);
  lv_obj_set_width(qrLbl, 100);
  lv_obj_set_pos(qrLbl, 215, 155);
}

// ══════════════════════════════════════════════════════════════════
//   SECTION 26E — TOUCH CALIBRATION
//   State machine polling XPT2046 directly for 4 corner presses.
//   Assumes library rotation matches display rotation (setRotation 1).
// ══════════════════════════════════════════════════════════════════
void cal_draw_target(int idx) {
  if (idx < 0 || idx > 3) return;
  lv_obj_set_pos(calCrosshair,
                 CAL_TARGETS[idx].x - 12,
                 CAL_TARGETS[idx].y - 12);
  char buf[48];
  snprintf(buf, sizeof(buf), "Tap the target  (%d/4)", idx + 1);
  lv_label_set_text(lblCalPrompt, buf);
}

void cal_finish_and_save() {
  // Derive min/max across the 4 raw samples (top-left & bottom-right diagonals)
  int16_t minx = cal_raw_x[0], maxx = cal_raw_x[0];
  int16_t miny = cal_raw_y[0], maxy = cal_raw_y[0];
  for (int i = 1; i < 4; i++) {
    if (cal_raw_x[i] < minx) minx = cal_raw_x[i];
    if (cal_raw_x[i] > maxx) maxx = cal_raw_x[i];
    if (cal_raw_y[i] < miny) miny = cal_raw_y[i];
    if (cal_raw_y[i] > maxy) maxy = cal_raw_y[i];
  }
  // Extend a touch beyond the tap points (targets were 10 px from edges).
  // Scale: (SCREEN - 2*inset) pixels spanned → extrapolate to edges.
  int16_t spanx = maxx - minx;
  int16_t spany = maxy - miny;
  float px_per_rawx = (float)(SCREEN_W - 2 * 10) / (float)(spanx == 0 ? 1 : spanx);
  float px_per_rawy = (float)(SCREEN_H - 2 * 10) / (float)(spany == 0 ? 1 : spany);
  ts_min_x = (int16_t)(minx - 10.0f / px_per_rawx);
  ts_max_x = (int16_t)(maxx + 10.0f / px_per_rawx);
  ts_min_y = (int16_t)(miny - 10.0f / px_per_rawy);
  ts_max_y = (int16_t)(maxy + 10.0f / px_per_rawy);

  preferences.putShort("ts_minx", ts_min_x);
  preferences.putShort("ts_maxx", ts_max_x);
  preferences.putShort("ts_miny", ts_min_y);
  preferences.putShort("ts_maxy", ts_max_y);

  cal_step = -1;
  if (calTimer) { lv_timer_del(calTimer); calTimer = NULL; }
  show_scrSettings();
}

static void cal_timer_cb(lv_timer_t *t) {
  if (cal_step < 0 || cal_step > 3) return;
  bool touched = ts.touched();
  if (touched) {
    TS_Point p = ts.getPoint();
    if (p.z > 300) {
      cal_last_raw_x = p.x;
      cal_last_raw_y = p.y;
      cal_was_touched = true;
    }
  } else if (cal_was_touched) {
    // Release edge — commit the last reading
    cal_raw_x[cal_step] = cal_last_raw_x;
    cal_raw_y[cal_step] = cal_last_raw_y;
    cal_was_touched = false;
    cal_step++;
    if (cal_step >= 4) cal_finish_and_save();
    else cal_draw_target(cal_step);
  }
}

void cal_begin() {
  cal_step = 0;
  cal_was_touched = false;
  cal_draw_target(0);
  if (!calTimer) calTimer = lv_timer_create(cal_timer_cb, 40, NULL);
}

static void calibrate_cancel_cb(lv_event_t *e) {
  cal_step = -1;
  if (calTimer) { lv_timer_del(calTimer); calTimer = NULL; }
  show_scrSettings();
}

static void build_scrCalibrate() {
  scrCalibrate = lv_obj_create(NULL);
  style_screen(scrCalibrate);
  lv_obj_clear_flag(scrCalibrate, LV_OBJ_FLAG_SCROLLABLE);

  // Crosshair: a 24x24 styled object with a centered "+" label
  calCrosshair = lv_obj_create(scrCalibrate);
  lv_obj_set_size(calCrosshair, 24, 24);
  lv_obj_set_pos(calCrosshair, 0, 0);
  lv_obj_set_style_bg_color    (calCrosshair, lv_color_hex(CLR_ACCENT), 0);
  lv_obj_set_style_bg_opa      (calCrosshair, LV_OPA_40, 0);
  lv_obj_set_style_border_color(calCrosshair, lv_color_hex(CLR_ACCENT), 0);
  lv_obj_set_style_border_width(calCrosshair, 2, 0);
  lv_obj_set_style_radius      (calCrosshair, 12, 0);
  lv_obj_clear_flag(calCrosshair, LV_OBJ_FLAG_CLICKABLE | LV_OBJ_FLAG_SCROLLABLE);
  lv_obj_t *plus = lv_label_create(calCrosshair);
  lv_label_set_text(plus, "+");
  lv_obj_set_style_text_color(plus, lv_color_hex(CLR_TXT), 0);
  lv_obj_set_style_text_font (plus, &lv_font_inter_16, 0);
  lv_obj_center(plus);

  lblCalPrompt = lv_label_create(scrCalibrate);
  lv_label_set_text(lblCalPrompt, "Tap the target  (1/4)");
  lv_obj_set_style_text_color(lblCalPrompt, lv_color_hex(CLR_TXT), 0);
  lv_obj_set_style_text_font (lblCalPrompt, &lv_font_inter_16, 0);
  lv_obj_align(lblCalPrompt, LV_ALIGN_CENTER, 0, -10);

  lv_obj_t *hint = lv_label_create(scrCalibrate);
  lv_label_set_text(hint,
    "Release your finger after\n"
    "each tap to advance.");
  lv_obj_set_style_text_color(hint, lv_color_hex(CLR_TXT_DIM), 0);
  lv_obj_set_style_text_font (hint, &lv_font_inter_12, 0);
  lv_obj_set_style_text_align(hint, LV_TEXT_ALIGN_CENTER, 0);
  lv_obj_align(hint, LV_ALIGN_CENTER, 0, 25);

  // Small cancel button near center — avoids being on any crosshair
  lv_obj_t *bCan = lv_btn_create(scrCalibrate);
  lv_obj_set_size(bCan, 90, 34);
  lv_obj_align(bCan, LV_ALIGN_CENTER, 0, 65);
  lv_obj_set_style_bg_color    (bCan, lv_color_hex(CLR_PANEL2), 0);
  lv_obj_set_style_border_color(bCan, lv_color_hex(CLR_BORDER), 0);
  lv_obj_set_style_border_width(bCan, 1, 0);
  lv_obj_set_style_radius      (bCan, 5, 0);
  lv_obj_set_style_text_color  (bCan, lv_color_hex(CLR_TXT),    0);
  lv_obj_set_style_shadow_width(bCan, 0, 0);
  lv_obj_add_event_cb(bCan, calibrate_cancel_cb, LV_EVENT_CLICKED, NULL);
  lv_obj_t *lCan = lv_label_create(bCan);
  lv_label_set_text(lCan, "Cancel");
  lv_obj_set_style_text_font(lCan, &lv_font_inter_14, 0);
  lv_obj_center(lCan);
}

// ══════════════════════════════════════════════════════════════════
//   SECTION 26F — RENAME (lv_keyboard + text area)
// ══════════════════════════════════════════════════════════════════
static void rename_back_cb(lv_event_t *e) {
  bool fromBuilder = rename_save_builder;
  int  tgt         = rename_target_idx;
  rename_save_builder = false;
  rename_target_idx   = -1;
  if (fromBuilder) {
    // Naming was cancelled — go back to the builder so the user can adjust
    // steps or choose Cancel explicitly. Builder state is preserved.
    show_scrBuilder();
  } else if (tgt >= 0 && tgt < saved_custom_count) {
    show_scrCustomDetail(tgt);
  } else {
    show_scrCustom();
  }
}

static void rename_save_cb(lv_event_t *e) {
  const char *txt = lv_textarea_get_text(renameTA);
  if (!txt || !*txt) {
    ui_show_alert("Empty name", "Name cannot be empty.");
    return;
  }

  if (rename_save_builder) {
    // Save-from-builder path — either create a new slot or overwrite the
    // slot we're editing. Steps come from builder_steps.
    int idx;
    if (rename_target_idx < 0) {
      if (saved_custom_count >= SAVED_CUSTOM_MAX) {
        ui_show_alert("Storage full", "Cannot save — 16 custom profiles maximum.");
        return;
      }
      idx = saved_custom_count++;
    } else {
      idx = rename_target_idx;
    }
    strncpy(saved_customs[idx].name, txt, PROFILE_NAME_LEN - 1);
    saved_customs[idx].name[PROFILE_NAME_LEN - 1] = 0;
    saved_customs[idx].step_count = builder_step_count;
    for (int i = 0; i < builder_step_count; i++)
      saved_customs[idx].steps[i] = builder_steps[i];
    saveCustomProfiles();

    // Sync the main-screen button if this was the currently-selected profile.
    if (selected_custom_idx == idx) {
      strncpy(selected_profile_name, saved_customs[idx].name, PROFILE_NAME_LEN - 1);
      selected_profile_name[PROFILE_NAME_LEN - 1] = 0;
      set_profile_button_label(selected_profile_name);
      refresh_profile_preview();
    }

    builder_step_count  = 0;
    builder_editing_idx = -1;
    builder_page        = 0;
    rename_save_builder = false;
    rename_target_idx   = -1;
    custom_list_page    = 0;
    show_scrCustom();
    return;
  }

  // Plain rename of an existing saved profile.
  if (rename_target_idx < 0 || rename_target_idx >= saved_custom_count) {
    show_scrCustom();
    return;
  }
  strncpy(saved_customs[rename_target_idx].name, txt, PROFILE_NAME_LEN - 1);
  saved_customs[rename_target_idx].name[PROFILE_NAME_LEN - 1] = 0;
  saveCustomProfiles();
  if (selected_custom_idx == rename_target_idx) {
    strncpy(selected_profile_name, saved_customs[rename_target_idx].name, PROFILE_NAME_LEN - 1);
    selected_profile_name[PROFILE_NAME_LEN - 1] = 0;
    set_profile_button_label(selected_profile_name);
  }
  int idx = rename_target_idx;
  rename_target_idx = -1;
  show_scrCustomDetail(idx);
}

static void build_scrRename() {
  scrRename = lv_obj_create(NULL);
  style_screen(scrRename);
  lv_obj_clear_flag(scrRename, LV_OBJ_FLAG_SCROLLABLE);
  add_back_button(scrRename, rename_back_cb);

  // Save button at top-right.
  lv_obj_t *bSave = lv_btn_create(scrRename);
  lv_obj_set_size(bSave, 56, 26);
  lv_obj_set_pos(bSave, SCREEN_W - 60, 6);
  lv_obj_set_style_bg_color    (bSave, lv_color_hex(CLR_SUCCESS_D), 0);
  lv_obj_set_style_bg_color    (bSave, lv_color_hex(CLR_SUCCESS),   LV_STATE_PRESSED);
  lv_obj_set_style_border_color(bSave, lv_color_hex(CLR_SUCCESS),   0);
  lv_obj_set_style_border_width(bSave, 1, 0);
  lv_obj_set_style_radius      (bSave, 5, 0);
  lv_obj_set_style_shadow_width(bSave, 0, 0);
  lv_obj_set_style_text_color  (bSave, lv_color_hex(CLR_TXT),       0);
  lv_obj_add_event_cb(bSave, rename_save_cb, LV_EVENT_CLICKED, NULL);
  lv_obj_t *lSave = lv_label_create(bSave);
  lv_label_set_text(lSave, "Save");
  lv_obj_set_style_text_font(lSave, &lv_font_inter_14, 0);
  lv_obj_center(lSave);

  // Centered title — text is set per visit by show_scrRename() to either
  // "Name profile" (new save) or "Rename profile" (renaming existing).
  lblRenameTitle = lv_label_create(scrRename);
  lv_label_set_text(lblRenameTitle, "Rename profile");
  lv_obj_set_style_text_color(lblRenameTitle, lv_color_hex(CLR_TXT), 0);
  lv_obj_set_style_text_font (lblRenameTitle, &lv_font_inter_16, 0);
  lv_obj_align(lblRenameTitle, LV_ALIGN_TOP_MID, 0, 10);

  // Textarea sits directly above the keyboard so the layout matches the
  // WiFi credentials screen. Keyboard at y=112..240; textarea at y=82..108.
  renameTA = lv_textarea_create(scrRename);
  lv_obj_set_size(renameTA, 280, 28);
  lv_obj_set_pos(renameTA, 20, 80);
  lv_textarea_set_one_line(renameTA, true);
  lv_textarea_set_max_length(renameTA, PROFILE_NAME_LEN - 1);
  lv_obj_set_style_bg_color    (renameTA, lv_color_hex(CLR_PANEL2), 0);
  lv_obj_set_style_border_color(renameTA, lv_color_hex(CLR_ACCENT), 0);
  lv_obj_set_style_border_width(renameTA, 1, 0);
  lv_obj_set_style_pad_all     (renameTA, 2, 0);
  lv_obj_set_style_text_color  (renameTA, lv_color_hex(CLR_TXT),    0);
  lv_obj_set_style_text_font   (renameTA, &lv_font_inter_14,   0);

  // Keyboard — same height (128) and position (y=112) as the WiFi screen
  // for visual consistency.
  renameKB = lv_keyboard_create(scrRename);
  lv_obj_remove_style_all(renameKB);
  lv_obj_set_size(renameKB, 320, 128);
  lv_obj_set_pos(renameKB, 0, 112);
  lv_keyboard_set_textarea(renameKB, renameTA);
  lv_keyboard_set_mode(renameKB, LV_KEYBOARD_MODE_TEXT_LOWER);

  // --- MAIN: zero every possible outer space ---
  lv_obj_set_style_pad_all    (renameKB, 0, LV_PART_MAIN);
  lv_obj_set_style_pad_row    (renameKB, 2, LV_PART_MAIN);
  lv_obj_set_style_pad_column (renameKB, 2, LV_PART_MAIN);
  lv_obj_set_style_border_width(renameKB, 0, LV_PART_MAIN);
  lv_obj_set_style_outline_width(renameKB, 0, LV_PART_MAIN);
  lv_obj_set_style_radius     (renameKB, 0, LV_PART_MAIN);
  lv_obj_set_style_shadow_width(renameKB, 0, LV_PART_MAIN);
  lv_obj_set_style_bg_opa     (renameKB, LV_OPA_COVER,           LV_PART_MAIN);
  lv_obj_set_style_bg_color   (renameKB, lv_color_hex(CLR_PANEL), LV_PART_MAIN);

  // --- ITEMS: button styling ---
  lv_obj_set_style_pad_all    (renameKB, 0, LV_PART_ITEMS);
  lv_obj_set_style_border_width(renameKB, 0, LV_PART_ITEMS);
  lv_obj_set_style_outline_width(renameKB, 0, LV_PART_ITEMS);
  lv_obj_set_style_shadow_width(renameKB, 0, LV_PART_ITEMS);
  lv_obj_set_style_radius     (renameKB, 2, LV_PART_ITEMS);
  lv_obj_set_style_bg_opa     (renameKB, LV_OPA_COVER,             LV_PART_ITEMS);
  lv_obj_set_style_bg_color   (renameKB, lv_color_hex(CLR_PANEL2), LV_PART_ITEMS);
  lv_obj_set_style_text_color (renameKB, lv_color_hex(CLR_TXT),    LV_PART_ITEMS);
  lv_obj_set_style_text_font  (renameKB, &lv_font_inter_14,   LV_PART_ITEMS);
}

// Pre-fill comes from:
//   rename_save_builder == true  → rename_default_name  (naming a new/edited save)
//   rename_target_idx   >= 0     → saved_customs[idx].name  (pure rename)
//   otherwise                   → empty
void show_scrRename() {
  const char *prefill = "";
  const char *title   = "Rename profile";
  if (rename_save_builder) {
    prefill = rename_default_name;
    // Naming a freshly built profile vs. naming the result of an edit;
    // both flow through here as save_builder=true. Either way it's "Name".
    title = "Name profile";
  } else if (rename_target_idx >= 0 && rename_target_idx < saved_custom_count) {
    prefill = saved_customs[rename_target_idx].name;
    title   = "Rename profile";
  }
  if (lblRenameTitle) lv_label_set_text(lblRenameTitle, title);
  lv_textarea_set_text(renameTA, prefill);
  lv_scr_load(scrRename);
}

// ══════════════════════════════════════════════════════════════════
//   SECTION 26G — WIFI: STAGE 1 (SSID PICKER)  +  STAGE 2 (PASSWORD)
//
//   Stage 1 (scrWifi):
//     • Tightly-spaced list of scanned networks
//     • Big up/down arrows shift the highlight cursor
//     • "Select" advances to stage 2 with that SSID
//     • "Rescan" re-runs the asynchronous scan
//   Stage 2 (scrWifiPass):
//     • One-line password textarea (masked)
//     • Full keyboard at the bottom
//     • Save commits to NVS and reconnects
// ══════════════════════════════════════════════════════════════════
static void wifi_back_cb(lv_event_t *e) { show_scrSettings(); }

static void wifi_up_cb(lv_event_t *e) {
  if (wifi_scan_count == 0) return;
  if (wifi_sel_idx > 0) {
    wifi_sel_idx--;
    if (wifi_sel_idx < wifi_list_top) wifi_list_top = wifi_sel_idx;
    refreshWifiList();
  }
}
static void wifi_down_cb(lv_event_t *e) {
  if (wifi_scan_count == 0) return;
  if (wifi_sel_idx < wifi_scan_count - 1) {
    wifi_sel_idx++;
    if (wifi_sel_idx >= wifi_list_top + WIFI_LIST_VISIBLE)
      wifi_list_top = wifi_sel_idx - WIFI_LIST_VISIBLE + 1;
    refreshWifiList();
  }
}
static void wifi_rescan_cb(lv_event_t *e) {
  wifiStartScan();
  refreshWifiList();
}
// Act on the currently-highlighted display row.
//   • saved + in range  → connect immediately with the stored password
//   • saved + offline   → block with an alert ("not currently visible")
//   • not saved         → advance to the password entry screen
static void wifi_select_cb(lv_event_t *e) {
  if (wifi_display_count == 0) {
    ui_show_alert("No network", "Wait for the scan to finish, or Rescan.");
    return;
  }
  if (wifi_sel_idx < 0 || wifi_sel_idx >= wifi_display_count) return;
  const WifiDisplayEntry &d = wifi_display[wifi_sel_idx];

  if (d.is_saved) {
    if (!d.in_range) {
      ui_show_alert("Out of range",
                    "This saved network is not currently visible.");
      return;
    }
    int idx = findSavedByName(d.ssid);
    if (idx < 0) return;
    // Move to slot 0 so subsequent auto-reconnects pick this one.
    if (idx != 0) {
      SavedNetwork tmp = saved_nets[idx];
      for (int i = idx; i > 0; i--) saved_nets[i] = saved_nets[i - 1];
      saved_nets[0] = tmp;
      saveSavedNets();
      idx = 0;
    }
    strncpy(wifi_ssid, saved_nets[idx].ssid, sizeof(wifi_ssid) - 1);
    wifi_ssid[sizeof(wifi_ssid) - 1] = 0;
    strncpy(wifi_pass, saved_nets[idx].pass, sizeof(wifi_pass) - 1);
    wifi_pass[sizeof(wifi_pass) - 1] = 0;
    // Stay on this screen — the state machine drives the title banner
    // and routes us to the password screen if it ends up failing.
    wifiAttemptConnect(wifi_ssid, wifi_pass);
    return;
  }

  // Unsaved network → password entry.
  strncpy(wifi_ssid, d.ssid, sizeof(wifi_ssid) - 1);
  wifi_ssid[sizeof(wifi_ssid) - 1] = 0;
  wifi_pass[0] = 0;     // start blank for a brand-new network
  show_scrWifiPass();
}

// Tap on a list row → move the cursor onto it and run the same action as
// the Select button. Slot index (0..WIFI_LIST_VISIBLE-1) comes via user_data.
static void wifi_row_tapped_cb(lv_event_t *e) {
  int slot = (int)(intptr_t)lv_event_get_user_data(e);
  int idx  = wifi_list_top + slot;
  if (idx < 0 || idx >= wifi_display_count) return;
  wifi_sel_idx = idx;
  refreshWifiList();
  wifi_select_cb(e);
}

// --- Stage 2: password ----------------------------------------------------
static void wifi_pass_back_cb(lv_event_t *e) { show_scrWifi(); }

static void wifi_save_cb(lv_event_t *e) {
  if (!wifi_ssid[0]) {
    ui_show_alert("No SSID", "Please pick a network first.");
    return;
  }
  const char *p = lv_textarea_get_text(wifiTA_pass);
  strncpy(wifi_pass, p ? p : "", sizeof(wifi_pass) - 1);
  wifi_pass[sizeof(wifi_pass) - 1] = 0;
  // Persist into the saved-networks list (insert or update by SSID).
  addOrUpdateSavedNet(wifi_ssid, wifi_pass);
  // Bounce back to the network list so the user sees connection status,
  // not into Settings. wifiAttemptConnect arms the state machine.
  wifiAttemptConnect(wifi_ssid, wifi_pass);
  show_scrWifi();
}

// --------------------------------------------------------------------------
static void build_scrWifi() {
  scrWifi = lv_obj_create(NULL);
  style_screen(scrWifi);
  lv_obj_clear_flag(scrWifi, LV_OBJ_FLAG_SCROLLABLE);
  add_back_button(scrWifi, wifi_back_cb);

  // Title — doubles as live status banner (scanning / connecting / failed
  // / connected). refreshWifiList() rewrites the text + color each frame.
  lblWifiTitle = lv_label_create(scrWifi);
  lv_label_set_text(lblWifiTitle, "WiFi Networks");
  lv_obj_set_style_text_color(lblWifiTitle, lv_color_hex(CLR_TXT), 0);
  lv_obj_set_style_text_font (lblWifiTitle, &lv_font_inter_16, 0);
  lv_obj_align(lblWifiTitle, LV_ALIGN_TOP_MID, 0, 10);

  // List panel (235 × 164) holds 8 rows × 20 px each.
  lv_obj_t *panel = lv_obj_create(scrWifi);
  lv_obj_set_size(panel, 235, 164);
  lv_obj_set_pos(panel, 5, 36);
  lv_obj_set_style_bg_color    (panel, lv_color_hex(CLR_PANEL),  0);
  lv_obj_set_style_border_color(panel, lv_color_hex(CLR_BORDER), 0);
  lv_obj_set_style_border_width(panel, 1, 0);
  lv_obj_set_style_radius      (panel, 4, 0);
  lv_obj_set_style_pad_all     (panel, 1, 0);
  lv_obj_clear_flag(panel, LV_OBJ_FLAG_SCROLLABLE);

  for (int i = 0; i < WIFI_LIST_VISIBLE; i++) {
    wifiListRow[i] = lv_obj_create(panel);
    lv_obj_set_size(wifiListRow[i], 231, 19);
    lv_obj_set_pos(wifiListRow[i], 0, i * 20);
    lv_obj_set_style_bg_color    (wifiListRow[i], lv_color_hex(CLR_PANEL2), 0);
    lv_obj_set_style_border_width(wifiListRow[i], 0, 0);
    lv_obj_set_style_radius      (wifiListRow[i], 0, 0);
    lv_obj_set_style_pad_all     (wifiListRow[i], 1, 0);
    lv_obj_clear_flag(wifiListRow[i], LV_OBJ_FLAG_SCROLLABLE);
    // Rows ARE clickable now — tap directly acts on the network.
    lv_obj_add_flag  (wifiListRow[i], LV_OBJ_FLAG_CLICKABLE);
    lv_obj_add_event_cb(wifiListRow[i], wifi_row_tapped_cb,
                        LV_EVENT_CLICKED, (void *)(intptr_t)i);

    // Saved indicator (left, 14 px)
    lblWifiSaved[i] = lv_label_create(wifiListRow[i]);
    lv_label_set_text(lblWifiSaved[i], "");
    lv_obj_set_style_text_font(lblWifiSaved[i], &lv_font_inter_12, 0);
    lv_obj_align(lblWifiSaved[i], LV_ALIGN_LEFT_MID, 2, 0);
    lv_obj_add_flag(lblWifiSaved[i], LV_OBJ_FLAG_HIDDEN);

    // SSID label (middle)
    wifiListLabel[i] = lv_label_create(wifiListRow[i]);
    lv_label_set_text(wifiListLabel[i], "");
    lv_obj_set_style_text_color(wifiListLabel[i], lv_color_hex(CLR_TXT), 0);
    lv_obj_set_style_text_font (wifiListLabel[i], &lv_font_inter_12, 0);
    lv_obj_align(wifiListLabel[i], LV_ALIGN_LEFT_MID, 18, 0);

    // Signal indicator (right)
    lblWifiSignal[i] = lv_label_create(wifiListRow[i]);
    lv_label_set_text(lblWifiSignal[i], "");
    lv_obj_set_style_text_font(lblWifiSignal[i], &lv_font_inter_14, 0);
    lv_obj_align(lblWifiSignal[i], LV_ALIGN_RIGHT_MID, -4, 0);

    lv_obj_add_flag(wifiListRow[i], LV_OBJ_FLAG_HIDDEN);
  }

  // Empty-state placeholder.
  lblWifiNoResults = lv_label_create(panel);
  lv_label_set_text(lblWifiNoResults, "Scanning...");
  lv_obj_set_style_text_color(lblWifiNoResults, lv_color_hex(CLR_TXT_DIM), 0);
  lv_obj_set_style_text_font (lblWifiNoResults, &lv_font_inter_14, 0);
  lv_obj_center(lblWifiNoResults);

  // Big up/down arrows on the right — same proportions as the profile
  // selector so the touch targets feel familiar.
  make_themed_btn(scrWifi, LV_SYMBOL_UP,   245,  36, 70, 80,
                  wifi_up_cb,   NULL, ROLE_NEUTRAL);
  make_themed_btn(scrWifi, LV_SYMBOL_DOWN, 245, 120, 70, 80,
                  wifi_down_cb, NULL, ROLE_NEUTRAL);

  // Bottom row: Select (wide, primary) + Rescan (narrow, neutral).
  make_themed_btn(scrWifi, "Select",   5, 205, 215, 33,
                  wifi_select_cb, NULL, ROLE_PRIMARY);
  make_themed_btn(scrWifi, "Rescan", 225, 205,  90, 33,
                  wifi_rescan_cb, NULL, ROLE_NEUTRAL);
}

static void build_scrWifiPass() {
  scrWifiPass = lv_obj_create(NULL);
  style_screen(scrWifiPass);
  lv_obj_clear_flag(scrWifiPass, LV_OBJ_FLAG_SCROLLABLE);
  add_back_button(scrWifiPass, wifi_pass_back_cb);

  // Top-right Save.
  lv_obj_t *bSave = lv_btn_create(scrWifiPass);
  lv_obj_set_size(bSave, 56, 26);
  lv_obj_set_pos(bSave, SCREEN_W - 60, 6);
  lv_obj_set_style_bg_color    (bSave, lv_color_hex(CLR_SUCCESS_D), 0);
  lv_obj_set_style_bg_color    (bSave, lv_color_hex(CLR_SUCCESS),   LV_STATE_PRESSED);
  lv_obj_set_style_border_color(bSave, lv_color_hex(CLR_SUCCESS),   0);
  lv_obj_set_style_border_width(bSave, 1, 0);
  lv_obj_set_style_radius      (bSave, 5, 0);
  lv_obj_set_style_shadow_width(bSave, 0, 0);
  lv_obj_set_style_text_color  (bSave, lv_color_hex(CLR_TXT),       0);
  lv_obj_add_event_cb(bSave, wifi_save_cb, LV_EVENT_CLICKED, NULL);
  lv_obj_t *lSave = lv_label_create(bSave);
  lv_label_set_text(lSave, "Save");
  lv_obj_set_style_text_font(lSave, &lv_font_inter_14, 0);
  lv_obj_center(lSave);

  // Network label — populated in show_scrWifiPass().
  lblWifiPassNetwork = lv_label_create(scrWifiPass);
  lv_label_set_text(lblWifiPassNetwork, "");
  lv_obj_set_style_text_color(lblWifiPassNetwork, lv_color_hex(CLR_TXT), 0);
  lv_obj_set_style_text_font (lblWifiPassNetwork, &lv_font_inter_14, 0);
  lv_obj_align(lblWifiPassNetwork, LV_ALIGN_TOP_MID, 0, 44);

  // Red retry subtitle — only visible when the user landed here because
  // the previous attempt failed (wifi_retry_due_to_fail).
  lblWifiPassRetry = lv_label_create(scrWifiPass);
  lv_label_set_text(lblWifiPassRetry, "Wrong password? Re-enter and Save.");
  lv_obj_set_style_text_color(lblWifiPassRetry, lv_color_hex(CLR_DANGER), 0);
  lv_obj_set_style_text_font (lblWifiPassRetry, &lv_font_inter_12, 0);
  lv_obj_align(lblWifiPassRetry, LV_ALIGN_TOP_MID, 0, 62);
  lv_obj_add_flag(lblWifiPassRetry, LV_OBJ_FLAG_HIDDEN);

  // Password textarea (masked) just above the keyboard.
  wifiTA_pass = lv_textarea_create(scrWifiPass);
  lv_obj_set_size(wifiTA_pass, 280, 28);
  lv_obj_set_pos(wifiTA_pass, 20, 80);
  lv_textarea_set_one_line(wifiTA_pass, true);
  lv_textarea_set_password_mode(wifiTA_pass, true);
  lv_textarea_set_max_length(wifiTA_pass, sizeof(wifi_pass) - 1);
  lv_obj_set_style_pad_all     (wifiTA_pass, 2, 0);
  lv_obj_set_style_bg_color    (wifiTA_pass, lv_color_hex(CLR_PANEL2), 0);
  lv_obj_set_style_border_color(wifiTA_pass, lv_color_hex(CLR_ACCENT), 0);
  lv_obj_set_style_border_width(wifiTA_pass, 1, 0);
  lv_obj_set_style_text_color  (wifiTA_pass, lv_color_hex(CLR_TXT),    0);
  lv_obj_set_style_text_font   (wifiTA_pass, &lv_font_inter_14,   0);

  // Keyboard — same recipe as the rename screen, 128 tall at y=112.
  wifiPassKB = lv_keyboard_create(scrWifiPass);
  lv_obj_remove_style_all(wifiPassKB);
  lv_obj_set_size(wifiPassKB, 320, 128);
  lv_obj_set_pos(wifiPassKB, 0, 112);
  lv_keyboard_set_textarea(wifiPassKB, wifiTA_pass);
  lv_keyboard_set_mode(wifiPassKB, LV_KEYBOARD_MODE_TEXT_LOWER);
  lv_obj_set_style_pad_all     (wifiPassKB, 0, LV_PART_MAIN);
  lv_obj_set_style_pad_row     (wifiPassKB, 2, LV_PART_MAIN);
  lv_obj_set_style_pad_column  (wifiPassKB, 2, LV_PART_MAIN);
  lv_obj_set_style_border_width(wifiPassKB, 0, LV_PART_MAIN);
  lv_obj_set_style_bg_opa      (wifiPassKB, LV_OPA_COVER,             LV_PART_MAIN);
  lv_obj_set_style_bg_color    (wifiPassKB, lv_color_hex(CLR_PANEL),  LV_PART_MAIN);
  lv_obj_set_style_pad_all     (wifiPassKB, 0,                        LV_PART_ITEMS);
  lv_obj_set_style_radius      (wifiPassKB, 2,                        LV_PART_ITEMS);
  lv_obj_set_style_bg_opa      (wifiPassKB, LV_OPA_COVER,             LV_PART_ITEMS);
  lv_obj_set_style_bg_color    (wifiPassKB, lv_color_hex(CLR_PANEL2), LV_PART_ITEMS);
  lv_obj_set_style_text_color  (wifiPassKB, lv_color_hex(CLR_TXT),    LV_PART_ITEMS);
  lv_obj_set_style_text_font   (wifiPassKB, &lv_font_inter_14,   LV_PART_ITEMS);
}

void show_scrWifi() {
  // Order matters: kick off the scan BEFORE the first paint so
  // refreshWifiList() observes wifi_scan_in_progress = true and shows
  // "Scanning...". Otherwise the user briefly sees "No networks found".
  wifiStartScan();
  refreshWifiList();
  lv_scr_load(scrWifi);
}

void show_scrWifiPass() {
  if (lblWifiPassNetwork) {
    char buf[48];
    snprintf(buf, sizeof(buf), "Network:  %s", wifi_ssid);
    lv_label_set_text(lblWifiPassNetwork, buf);
  }
  // Show the red "Wrong password?" subtitle only when we got here as a
  // result of a failed connection. Manual entry from the picker doesn't
  // need the warning. The flag is consumed (cleared) here so a Back-and-
  // forth doesn't keep flashing it.
  if (lblWifiPassRetry) {
    if (wifi_retry_due_to_fail) {
      lv_obj_clear_flag(lblWifiPassRetry, LV_OBJ_FLAG_HIDDEN);
    } else {
      lv_obj_add_flag(lblWifiPassRetry, LV_OBJ_FLAG_HIDDEN);
    }
  }
  wifi_retry_due_to_fail = false;

  // Pre-fill the password if the saved one belongs to this SSID; otherwise
  // start blank.
  lv_textarea_set_text(wifiTA_pass, wifi_pass);
  lv_keyboard_set_textarea(wifiPassKB, wifiTA_pass);
  lv_scr_load(scrWifiPass);
}

// ══════════════════════════════════════════════════════════════════
//   SECTION 26H — OTA PROGRESS SCREEN
//   Driven from inside performUpdate()'s blocking loop via the
//   httpUpdate.onProgress callback, which pumps lv_task_handler() each
//   tick so the bar and percentage stay live during the download.
// ══════════════════════════════════════════════════════════════════
static void build_scrOTA() {
  scrOTA = lv_obj_create(NULL);
  style_screen(scrOTA);
  lv_obj_clear_flag(scrOTA, LV_OBJ_FLAG_SCROLLABLE);

  lv_obj_t *title = lv_label_create(scrOTA);
  lv_label_set_text(title, "Updating Firmware");
  lv_obj_set_style_text_color(title, lv_color_hex(CLR_TXT), 0);
  lv_obj_set_style_text_font (title, &lv_font_inter_16, 0);
  lv_obj_align(title, LV_ALIGN_TOP_MID, 0, 28);

  lblOTAVersions = lv_label_create(scrOTA);
  lv_label_set_text(lblOTAVersions, "");
  lv_obj_set_style_text_color(lblOTAVersions, lv_color_hex(CLR_TXT_DIM), 0);
  lv_obj_set_style_text_font (lblOTAVersions, &lv_font_inter_14, 0);
  lv_obj_align(lblOTAVersions, LV_ALIGN_TOP_MID, 0, 60);

  barOTA = lv_bar_create(scrOTA);
  lv_obj_set_size(barOTA, 280, 22);
  lv_obj_align(barOTA, LV_ALIGN_CENTER, 0, 0);
  lv_bar_set_range(barOTA, 0, 100);
  lv_bar_set_value(barOTA, 0, LV_ANIM_OFF);
  lv_obj_set_style_bg_color    (barOTA, lv_color_hex(CLR_PANEL2), LV_PART_MAIN);
  lv_obj_set_style_bg_opa      (barOTA, LV_OPA_COVER,            LV_PART_MAIN);
  lv_obj_set_style_border_color(barOTA, lv_color_hex(CLR_BORDER), LV_PART_MAIN);
  lv_obj_set_style_border_width(barOTA, 1,                        LV_PART_MAIN);
  lv_obj_set_style_radius      (barOTA, 4,                        LV_PART_MAIN);
  lv_obj_set_style_bg_color    (barOTA, lv_color_hex(CLR_ACCENT), LV_PART_INDICATOR);
  lv_obj_set_style_bg_opa      (barOTA, LV_OPA_COVER,            LV_PART_INDICATOR);
  lv_obj_set_style_radius      (barOTA, 3,                        LV_PART_INDICATOR);

  lblOTAStatus = lv_label_create(scrOTA);
  lv_label_set_text(lblOTAStatus, "Connecting...");
  lv_obj_set_style_text_color(lblOTAStatus, lv_color_hex(CLR_TXT), 0);
  lv_obj_set_style_text_font (lblOTAStatus, &lv_font_inter_14, 0);
  lv_obj_align(lblOTAStatus, LV_ALIGN_CENTER, 0, 30);

  lv_obj_t *warn = lv_label_create(scrOTA);
  lv_label_set_text(warn, LV_SYMBOL_WARNING "  Do not power off the device.");
  lv_obj_set_style_text_color(warn, lv_color_hex(CLR_AMBER), 0);
  lv_obj_set_style_text_font (warn, &lv_font_inter_12, 0);
  lv_obj_align(warn, LV_ALIGN_BOTTOM_MID, 0, -22);
}

void show_scrOTA() {
  if (lblOTAVersions) {
    char buf[64];
    snprintf(buf, sizeof(buf), "%s  >>  %s", FIRMWARE_VERSION, ota_remote_version);
    lv_label_set_text(lblOTAVersions, buf);
  }
  if (lblOTAStatus) lv_label_set_text(lblOTAStatus, "Connecting...");
  if (barOTA)       lv_bar_set_value(barOTA, 0, LV_ANIM_OFF);
  lv_scr_load(scrOTA);
}

// Next unused "Custom Profile N" in sequence. Writes into out[].
static void generate_next_custom_name(char *out, size_t out_size) {
  int used_max = 0;
  for (int i = 0; i < saved_custom_count; i++) {
    int n = 0;
    if (sscanf(saved_customs[i].name, "Custom Profile %d", &n) == 1) {
      if (n > used_max) used_max = n;
    }
  }
  snprintf(out, out_size, "Custom Profile %d", used_max + 1);
}

// ══════════════════════════════════════════════════════════════════
//   SECTION 27 — SCREEN LOADERS
// ══════════════════════════════════════════════════════════════════
void show_scrMain()      { lv_scr_load(scrMain); }
void show_scrMaterial()  { lv_scr_load(scrMaterial); }
void show_scrHousehold() { lv_scr_load(scrHousehold); }
void show_scrEngineer()  { refresh_eng_page();    lv_scr_load(scrEngineer); }
void show_scrCustom()    { refresh_custom_list(); lv_scr_load(scrCustom); }
void show_scrBuilder() {
  if (lblBuilderTitle) {
    if (builder_editing_idx >= 0 && builder_editing_idx < saved_custom_count) {
      char buf[PROFILE_NAME_LEN + 12];
      snprintf(buf, sizeof(buf), "Edit: %s",
               saved_customs[builder_editing_idx].name);
      lv_label_set_text(lblBuilderTitle, buf);
    } else {
      lv_label_set_text(lblBuilderTitle, "New Custom Profile");
    }
  }
  refresh_builder_page();
  lv_scr_load(scrBuilder);
}
void show_scrAddType()   { lv_scr_load(scrAddType); }
void show_scrSettings()  { lv_scr_load(scrSettings); }
void show_scrFullGraph() { lv_scr_load(scrFullGraph); }
void show_scrCalibrate() {
  lv_scr_load(scrCalibrate);
  cal_begin();
}

// ══════════════════════════════════════════════════════════════════
//   SECTION 28 — UI INIT, BLINK TIMER, PERIODIC UPDATE
// ══════════════════════════════════════════════════════════════════

// Warning triangle blinks on the START/STOP button whenever the
// oven is actively heating. When idle, the button is a solid green
// START. When a profile is running, it's "⚠ STOP" with the triangle
// toggling between bright amber and dim amber. When heating without
// a profile (manual SET/RAMP from serial), it's "⚠ HOT" in place of
// the START label but the click still walks the normal selection
// path — the warning exists so the user knows the oven is live.
// The heating indicator now lives on the gauge (a small ⚠ glyph at the
// top-right of the gauge panel). The start/stop button stays static:
// green "START" when idle, red "STOP" when a profile is running.
static void blink_timer_cb(lv_timer_t *t) {
  blink_phase = !blink_phase;

  // Gauge-side warning glyph — blink red ↔ dim-red while the oven is live.
  if (lblGaugeWarn) {
    if (heaterActive()) {
      lv_obj_clear_flag(lblGaugeWarn, LV_OBJ_FLAG_HIDDEN);
      lv_obj_set_style_text_color(lblGaugeWarn,
        blink_phase ? lv_color_hex(CLR_DANGER)
                    : lv_color_hex(CLR_DANGER_D),
        0);
    } else {
      lv_obj_add_flag(lblGaugeWarn, LV_OBJ_FLAG_HIDDEN);
    }
  }

  // Keep the START/STOP button in sync with profile state (static, no blink).
  if (!btnStartStop || !lblBtnStart) return;
  if (profile_state > 0) {
    lv_obj_set_style_bg_color    (btnStartStop, lv_color_hex(CLR_DANGER_D), 0);
    lv_obj_set_style_bg_color    (btnStartStop, lv_color_hex(CLR_DANGER),   LV_STATE_PRESSED);
    lv_obj_set_style_border_color(btnStartStop, lv_color_hex(CLR_DANGER),   0);
    lv_obj_set_style_border_width(btnStartStop, 1, 0);
    lv_label_set_text(lblBtnStart, "STOP");
  } else {
    lv_obj_set_style_bg_color    (btnStartStop, lv_color_hex(CLR_SUCCESS_D), 0);
    lv_obj_set_style_bg_color    (btnStartStop, lv_color_hex(CLR_SUCCESS),   LV_STATE_PRESSED);
    lv_obj_set_style_border_color(btnStartStop, lv_color_hex(CLR_SUCCESS),   0);
    lv_obj_set_style_border_width(btnStartStop, 1, 0);
    lv_label_set_text(lblBtnStart, "START");
  }

  // Visually disable the Select Profile button while a profile is running.
  // Click is still routed through btn_profile_clicked which raises an
  // alert — the styling here is just so the user can tell at a glance.
  if (btnProfile) {
    if (profile_state > 0) {
      lv_obj_set_style_bg_color    (btnProfile, lv_color_hex(CLR_PANEL),  0);
      lv_obj_set_style_border_color(btnProfile, lv_color_hex(CLR_BORDER), 0);
      lv_obj_set_style_text_color  (btnProfile, lv_color_hex(CLR_TXT_DIM), 0);
    } else {
      lv_obj_set_style_bg_color    (btnProfile, lv_color_hex(CLR_ACCENT_D), 0);
      lv_obj_set_style_border_color(btnProfile, lv_color_hex(CLR_ACCENT),  0);
      lv_obj_set_style_text_color  (btnProfile, lv_color_hex(CLR_TXT),     0);
    }
  }
}

void ui_init() {
  build_scrMain();
  build_scrMaterial();
  build_scrHousehold();
  build_scrEngineer();
  build_scrCustom();
  build_scrCustomDetail();
  build_scrBuilder();
  build_scrAddType();
  build_scrKeypad();
  build_scrFullGraph();
  build_scrSettings();
  build_scrCalibrate();
  build_scrRename();
  build_scrWifi();
  build_scrWifiPass();
  build_scrOTA();
  refresh_eng_page();
  refresh_custom_list();
  refresh_builder_page();
  set_main_xaxis_idle();
  set_full_xaxis_idle();

  lv_scr_load(scrMain);

  blinkTimer = lv_timer_create(blink_timer_cb, 500, NULL);
}

void ui_update() {
  if (!lblTempVal) return;

  // Fire the completion popup here (UI-thread context) rather than
  // inside profileAdvanceStep (control-loop context).
  if (profile_completed_popup_pending) {
    profile_completed_popup_pending = false;
    ui_show_info("Profile complete", "Profile completed successfully.");
  }

  // OTA update prompt — raised by the boot-time check once WiFi is up and
  // the server's manifest reports a newer firmware.
  if (ota_prompt_pending) {
    ota_prompt_pending = false;
    char body[160];
    snprintf(body, sizeof(body),
             "A new firmware (%s) is available. Current: %s. Install now?",
             ota_remote_version, FIRMWARE_VERSION);
    ui_show_messagebox("Update available", body,
                       "Install", "Later",
                       [](lv_event_t *e) { execute_ota_update_now = true; });
  }

  // Gauge (clamped to arc range) + integer temp readout. lroundf returns
  // the nearest integer away from zero — guarantees 25.5 → 26, 25.4 → 25,
  // without the toolchain-dependent truncation that a plain (int) cast
  // can exhibit when fed a float literal.
  long tempI = lroundf(current_temp);
  long tempClamp = tempI;
  if (tempClamp < 20)  tempClamp = 20;
  if (tempClamp > 200) tempClamp = 200;
  lv_arc_set_value(arcTemp, (int)tempClamp);

  char buf[32];
  snprintf(buf, sizeof(buf), "%ld\xC2\xB0", tempI);
  lv_label_set_text(lblTempVal, buf);

  snprintf(buf, sizeof(buf), "SP %ld\xC2\xB0", lroundf(current_setpoint));
  lv_label_set_text(lblSetpoint, buf);

  // Mode label
  const char *mode = "IDLE";
  if      (tune_state > 0)    mode = "TUNE";
  else if (learn_state > 0)   mode = "LEARN";
  else if (profile_state > 0) mode = "PROFILE";
  else if (is_ramping)        mode = "RAMP";
  else if (setpoint > 25.0f)  mode = "HOLD";
  lv_label_set_text(lblMode, mode);

  // Profile button label — the blink timer handles the START/STOP side
  set_profile_button_label(profile_is_selected ? selected_profile_name : "Select Profile");
}
