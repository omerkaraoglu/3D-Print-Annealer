#pragma once
// ══════════════════════════════════════════════════════════════════
//  Thermocouple_ADS1115.h — Rev3.0 K-type thermocouple front end
//
//  Replaces the MAX6675 of Rev2.1 with:
//    • TI ADS1115 16-bit ΔΣ ADC on the I2C bus (address 0x48, ALERT/RDY
//      on IO35), AIN0-AIN1 differential, PGA ±256 mV (gain 16, LSB
//      7.8125 µV ≈ 0.19 °C for type K), 16 SPS single-shot.
//      10 MΩ bias resistors on the board pull the inputs to the rail when
//      the thermocouple is open → reading saturates → reported as NAN.
//    • Cold-junction sensor: Murata NCP18XH103 10 k NTC (B25/50 = 3380 K,
//      B25/85 = 3434 K) in a 10 k 1 % divider from 3.3 V on AIN2, read
//      single-ended with PGA ±4.096 V.
//    • AIN3 measures the 3.3 V rail through a 10 k / 10 k divider (half rail,
//      so it stays inside the ADS1115 input range), and the NTC divider is
//      evaluated RATIOMETRICALLY (counts_AIN2 / (2 * counts_AIN3)): the rail voltage and the
//      PGA gain error cancel. If AIN3 is not wired (or reads nonsense) the
//      code falls back to assuming a nominal 3.300 V rail. Set
//      CJ_USE_AIN3_REF to 0 to force the fallback.
//    • NIST ITS-90 type-K polynomials: forward E(T) for the cold-junction
//      EMF, inverse T(E) over −200..0 °C, 0..500 °C and 500..1372 °C.
//
//  readThermocouple() keeps the MAX6675 contract used by every caller:
//  returns °C or NAN on fault. The ADC work is a non-blocking state machine
//  (thermocouplePoll(), called from loop()) so the 62.5 ms conversion never
//  stalls the UI; the control loop simply picks up the newest sample.
//
//  Divider orientation (CJ_NTC_TO_GND):
//     1 → 3V3 ─[10 k 1 %]─┬─ AIN2        (NTC pulls AIN2 towards GND)
//                         └─[NTC]─ GND
//     0 → 3V3 ─[NTC TH220]─┬─ AIN2       ← Rev3.0 schematic (Rev3_Thermocouple.kicad_sch)
//                          └─[R225 10 k 0.1 %]─ GND
//  Reference: AIN3 = 3V3 / 2 through R226/R227 (10 k / 10 k 0.1 %), see CJ_REF_DIVIDER.
//  Flip the macro if the cold-junction temperature reads "upside down"
//  (i.e. goes DOWN when you warm the sensor). Check with the `TC` command.
// ══════════════════════════════════════════════════════════════════
#include <Arduino.h>
#include <Wire.h>
#include <math.h>
#include <Adafruit_ADS1X15.h>

#ifndef ADS1115_I2C_ADDR
#define ADS1115_I2C_ADDR   0x48
#endif
#ifndef ADS_RDY_PIN
#define ADS_RDY_PIN        35
#endif

#define CJ_NTC_TO_GND      0          // Rev3.0: NTC to 3V3, R225 to GND (see wiring note above)
#define CJ_USE_AIN3_REF    1          // ratiometric against the half-rail reference on AIN3
#define CJ_REF_DIVIDER     2.0f       // AIN3 = 3V3 / 2 (R226/R227 10 k / 10 k)
#define CJ_R_FIXED_OHM     10000.0f   // 10 k 1 % divider resistor
#define CJ_NTC_R25_OHM     10000.0f   // NCP18XH103: 10 k at 25 °C
#define CJ_NTC_BETA        3380.0f    // B(25/50) — right range for a cold junction;
                                      // use 3434.0f (B25/85) if it runs >50 °C
#define CJ_VDD_NOMINAL     3.300f     // fallback rail voltage when AIN3 is unusable
#define CJ_PERIOD_MS       2000UL     // cold-junction refresh period (slow-moving)
#define TC_STALE_MS        1500UL     // no fresh TC sample for this long → NAN (fault)
#define TC_CONV_TIMEOUT_MS 400UL      // conversion never finished → restart (I2C hiccup)

// ADS1115 scale factors
#define ADS_LSB_MV_GAIN16  0.0078125f // 256 mV / 32768
#define ADS_LSB_V_GAIN1    0.000125f  // 4.096 V / 32768
#define ADS_SATURATION     32000      // counts: ±FS minus margin → open input
#define TC_MV_MIN         -10.0f      // below −200 °C: not a real reading
#define TC_MV_MAX          60.0f      // above 1372 °C: not a real reading

static Adafruit_ADS1115 ads;

// ---------------------------------------------------------------- NIST ITS-90 type K
// E(T) in mV for the cold junction (T in °C). −270..0 and 0..1372 °C.
static float typeK_emf_mV(float t) {
  double T = t, E = 0.0;
  if (T < 0.0) {
    static const double c[] = {
       0.000000000000E+00,  0.394501280250E-01,  0.236223735980E-04,
      -0.328589067840E-06, -0.499048287770E-08, -0.675090591730E-10,
      -0.574103274280E-12, -0.310888728940E-14, -0.104516093650E-16,
      -0.198892668780E-19, -0.163226974860E-22 };
    for (int i = 10; i >= 0; i--) E = E * T + c[i];
  } else {
    static const double c[] = {
      -0.176004136860E-01,  0.389212049750E-01,  0.185587700320E-04,
      -0.994575928740E-07,  0.318409457190E-09, -0.560728448890E-12,
       0.560750590590E-15, -0.320207200030E-18,  0.971511471520E-22,
      -0.121047212750E-25 };
    for (int i = 9; i >= 0; i--) E = E * T + c[i];
    const double a0 = 0.118597600000E+00, a1 = -0.118343200000E-03, a2 = 0.126968600000E+03;
    E += a0 * exp(a1 * (T - a2) * (T - a2));
  }
  return (float)E;
}

// T(E) in °C from the total (compensated) EMF in mV. Three NIST ranges.
static float typeK_temp_from_mV(float e_mV) {
  double E = e_mV, T = 0.0;
  if (E < 0.0) {                       // −200 .. 0 °C  (−5.891 .. 0 mV)
    static const double d[] = {
       0.0000000E+00,  2.5173462E+01, -1.1662878E+00, -1.0833638E+00,
      -8.9773540E-01, -3.7342377E-01, -8.6632643E-02, -1.0450598E-02,
      -5.1920577E-04 };
    for (int i = 8; i >= 0; i--) T = T * E + d[i];
  } else if (E < 20.644) {             // 0 .. 500 °C  (0 .. 20.644 mV)
    static const double d[] = {
       0.000000E+00,  2.508355E+01,  7.860106E-02, -2.503131E-01,
       8.315270E-02, -1.228034E-02,  9.804036E-04, -4.413030E-05,
       1.057734E-06, -1.052755E-08 };
    for (int i = 9; i >= 0; i--) T = T * E + d[i];
  } else {                             // 500 .. 1372 °C  (20.644 .. 54.886 mV)
    static const double d[] = {
      -1.318058E+02,  4.830222E+01, -1.646031E+00,  5.464731E-02,
      -9.650715E-04,  8.802193E-06, -3.110810E-08 };
    for (int i = 6; i >= 0; i--) T = T * E + d[i];
  }
  return (float)T;
}

// ---------------------------------------------------------------- NTC cold junction
// ratio = V_AIN2 / V_rail (0..1). Beta equation around 25 °C.
static float ntc_temp_from_ratio(float r) {
  if (r < 0.005f) r = 0.005f;
  if (r > 0.995f) r = 0.995f;
#if CJ_NTC_TO_GND
  float r_ntc = CJ_R_FIXED_OHM * r / (1.0f - r);
#else
  float r_ntc = CJ_R_FIXED_OHM * (1.0f - r) / r;
#endif
  float inv_t = 1.0f / 298.15f + logf(r_ntc / CJ_NTC_R25_OHM) / CJ_NTC_BETA;
  return 1.0f / inv_t - 273.15f;
}

// ---------------------------------------------------------------- state machine
enum TcState { TC_IDLE, TC_WAIT_TC, TC_WAIT_NTC, TC_WAIT_REF };

static bool     tc_adc_ok        = false;
static TcState  tc_state         = TC_IDLE;
static uint32_t tc_conv_start_ms = 0;
static uint32_t tc_conv_expect_ms= 0;
static uint32_t tc_cj_last_ms    = 0;
static uint32_t tc_sample_ms     = 0;       // millis() of the last good TC sample
static bool     tc_have_cj       = false;
static int16_t  tc_raw_tc        = 0;
static int16_t  tc_raw_ntc       = 0;
static int16_t  tc_raw_ref       = 0;
static float    tc_mV            = 0.0f;    // thermocouple EMF (uncompensated)
static float    tc_cj_c          = 25.0f;   // cold-junction temperature
static float    tc_cj_ratio      = 0.5f;
static bool     tc_ref_used      = false;   // true when AIN3 was usable
static bool     tc_open          = false;
static float    tc_temp_c        = NAN;     // latest compensated reading

static void tc_start(uint16_t mux, adsGain_t gain, uint16_t rate, uint32_t expect_ms, TcState next) {
  ads.setGain(gain);
  ads.setDataRate(rate);
  ads.startADCReading(mux, /*continuous=*/false);   // also arms ALERT/RDY as RDY
  tc_conv_start_ms  = millis();
  tc_conv_expect_ms = expect_ms;
  tc_state          = next;
}

static void tc_start_tc()  { tc_start(ADS1X15_REG_CONFIG_MUX_DIFF_0_1, GAIN_SIXTEEN, RATE_ADS1115_16SPS,  63, TC_WAIT_TC);  }
static void tc_start_ntc() { tc_start(ADS1X15_REG_CONFIG_MUX_SINGLE_2, GAIN_ONE,     RATE_ADS1115_128SPS,  8, TC_WAIT_NTC); }
static void tc_start_ref() { tc_start(ADS1X15_REG_CONFIG_MUX_SINGLE_3, GAIN_ONE,     RATE_ADS1115_128SPS,  8, TC_WAIT_REF); }

// Conversion-ready check. In single-shot mode the ADS1115 drives ALERT/RDY
// LOW when a conversion completes (RDY mode: Hi_thresh MSB=1, Lo_thresh
// MSB=0, which Adafruit's startADCReading() programs). A HIGH pin means
// "still busy" — as long as the pull-up is present. If the pin stays HIGH
// well past the expected conversion time we stop trusting it and fall back
// to the OS bit in the config register, which is always authoritative.
static bool tc_conversion_ready() {
  uint32_t elapsed = millis() - tc_conv_start_ms;
  if (digitalRead(ADS_RDY_PIN) == HIGH && elapsed < tc_conv_expect_ms * 2 + 10) return false;
  return ads.conversionComplete();
}

static void tc_compute() {
  tc_mV = (float)tc_raw_tc * ADS_LSB_MV_GAIN16;
  // Open thermocouple: the 10 M bias resistors drag the differential input
  // to the rail → the PGA saturates. Anything outside the physical type-K
  // span is a fault too.
  if (tc_raw_tc >= ADS_SATURATION || tc_raw_tc <= -ADS_SATURATION ||
      tc_mV < TC_MV_MIN || tc_mV > TC_MV_MAX) {
    tc_open   = true;
    tc_temp_c = NAN;
    return;
  }
  tc_open = false;
  float e_total = tc_mV + typeK_emf_mV(tc_cj_c);   // cold-junction compensation
  float t = typeK_temp_from_mV(e_total);
  if (t < -50.0f || t > 600.0f || isnan(t)) { tc_temp_c = NAN; return; }
  tc_temp_c   = t;
  tc_sample_ms = millis();
}

static void tc_compute_cj() {
  float ratio;
#if CJ_USE_AIN3_REF
  // AIN3 = 3V3 / CJ_REF_DIVIDER: 1.65 V -> 13200 counts nominal at 125 µV/LSB.
  // Accept a rail of 2.5..3.6 V (10000..14400 counts for the half-rail divider).
  if (tc_raw_ref > (int)(20000 / CJ_REF_DIVIDER) && tc_raw_ref < (int)(28800 / CJ_REF_DIVIDER)) {
    ratio = (float)tc_raw_ntc / ((float)tc_raw_ref * CJ_REF_DIVIDER);
    tc_ref_used = true;
  } else
#endif
  {
    ratio = ((float)tc_raw_ntc * ADS_LSB_V_GAIN1) / CJ_VDD_NOMINAL;
    tc_ref_used = false;
  }
  tc_cj_ratio = ratio;
  float cj = ntc_temp_from_ratio(ratio);
  if (cj > -30.0f && cj < 120.0f) {
    tc_cj_c   = cj;
    tc_have_cj = true;
  }
  tc_cj_last_ms = millis();
}

// Pump the ADC. Cheap when nothing is ready (one GPIO read, at most one
// 2-byte I2C register read). Sequence: TC, TC, ... and every CJ_PERIOD_MS
// an NTC + reference pair is slipped in (~16 ms at 128 SPS).
static void thermocouplePoll() {
  if (!tc_adc_ok) return;
  uint32_t now = millis();

  if (tc_state != TC_IDLE && now - tc_conv_start_ms > TC_CONV_TIMEOUT_MS) {
    tc_state = TC_IDLE;              // lost conversion → restart the cycle
  }

  switch (tc_state) {
    case TC_IDLE:
      tc_start_tc();
      break;

    case TC_WAIT_TC:
      if (!tc_conversion_ready()) break;
      tc_raw_tc = ads.getLastConversionResults();
      tc_compute();
      if (!tc_have_cj || now - tc_cj_last_ms >= CJ_PERIOD_MS) tc_start_ntc();
      else                                                     tc_start_tc();
      break;

    case TC_WAIT_NTC:
      if (!tc_conversion_ready()) break;
      tc_raw_ntc = ads.getLastConversionResults();
#if CJ_USE_AIN3_REF
      tc_start_ref();
#else
      tc_compute_cj();
      tc_start_tc();
#endif
      break;

    case TC_WAIT_REF:
      if (!tc_conversion_ready()) break;
      tc_raw_ref = ads.getLastConversionResults();
      tc_compute_cj();
      tc_start_tc();
      break;
  }
}

// MAX6675-compatible accessor: °C, or NAN when the ADC is missing, the
// thermocouple is open / out of range, or no fresh sample arrived lately.
static float readThermocouple() {
  if (!tc_adc_ok || tc_open || isnan(tc_temp_c)) return NAN;
  if (millis() - tc_sample_ms > TC_STALE_MS)      return NAN;
  return tc_temp_c;
}

// Bring the ADS1115 up and block for one complete acquisition (TC + NTC +
// reference, ~100-150 ms) so the very first readThermocouple() is real.
// Wire.begin() must have been called already.
static void thermocoupleInit() {
  pinMode(ADS_RDY_PIN, INPUT);          // IO35 is input-only, no internal pull-up
  tc_adc_ok = ads.begin(ADS1115_I2C_ADDR, &Wire);
  if (!tc_adc_ok) {
    Serial.println("[TC] ADS1115 not found at 0x48 — thermocouple reads NAN (heater locked out).");
    return;
  }
  tc_state  = TC_IDLE;
  tc_have_cj = false;
  uint32_t t0 = millis();
  while (millis() - t0 < 400) {
    thermocouplePoll();
    if (tc_have_cj && (tc_open || !isnan(tc_temp_c))) {
      // We have a CJ value; make sure the TC reading was computed *after* it.
      if (tc_state == TC_WAIT_TC && tc_sample_ms >= tc_cj_last_ms) break;
      if (tc_open) break;
    }
    delay(1);
  }
  Serial.printf("[TC] ADS1115 ready. TC=%.3f mV  CJ=%.2f C (%s)  T=%.2f C%s\n",
                tc_mV, tc_cj_c, tc_ref_used ? "ratiometric" : "nominal 3.3 V",
                tc_temp_c, tc_open ? "  OPEN" : "");
}

// Serial `TC` command.
static void thermocouplePrintDebug() {
  Serial.println();
  Serial.printf("[TC] adc_ok=%d state=%d open=%d\n", (int)tc_adc_ok, (int)tc_state, (int)tc_open);
  Serial.printf("[TC] raw: tc=%d ntc=%d ref=%d  (sample age %lu ms)\n",
                (int)tc_raw_tc, (int)tc_raw_ntc, (int)tc_raw_ref,
                (unsigned long)(millis() - tc_sample_ms));
  Serial.printf("[TC] EMF=%.4f mV  CJ=%.2f C (ratio %.4f, %s)  E_cj=%.4f mV\n",
                tc_mV, tc_cj_c, tc_cj_ratio, tc_ref_used ? "ratiometric" : "nominal rail",
                typeK_emf_mV(tc_cj_c));
  Serial.printf("[TC] T=%.2f C   readThermocouple()=%.2f\n", tc_temp_c, readThermocouple());
}
