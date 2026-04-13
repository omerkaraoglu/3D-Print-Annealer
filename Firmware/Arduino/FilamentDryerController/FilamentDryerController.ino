/*
 * Filament Dryer Controller - ESP32-WROOM-32E
 *
 * Hardware:
 *   - 500W PTC heater via onboard triac (phase-angle control)
 *   - Zero-cross detector (active-low, falling edge 230us before true ZC)
 *   - MAX6675 thermocouple interface (VSPI)
 *
 * Pins:
 *   ZCD   = IO34 (input only, falling-edge interrupt)
 *   TRIAC = IO33 (gate pulse output)
 *   MAX6675 CS = IO13, SCK = IO18, MISO = IO19
 *
 * Serial commands:
 *   TUNE  - Astrom-Hagglund relay feedback auto-tune at 100C,
 *           then Tyreus-Luyben PID tuning, results saved to EEPROM
 *   SET   - Prompts for setpoint (20-200C), then runs PID control
 *
 * Triac constraints:
 *   - Max firing angle (alpha) = 3000us (~60 deg at 50Hz)
 *   - Alpha step = 3us, giving 1000 discrete steps
 *   - Gate pulse width = 150us
 *   - ZCD offset compensation = 230us
 *
 * Power control:
 *   Phase-angle control for power >= ~85% (alpha 0..3000us).
 *   Burst-mode cycle-skipping for power < 85%.
 *   Proper RMS power-to-alpha conversion for resistive load.
 *
 * NOTE: Built for ESP32 Arduino Core 2.x timer API.
 */

#include <SPI.h>
#include <EEPROM.h>
#include <math.h>

// ======================== PIN DEFINITIONS ========================
#define ZCD_PIN          34
#define TRIAC_PIN        33
#define MAX6675_CS_PIN   13

// ======================== MAINS / TRIAC ========================
#define HALF_PERIOD_US   10000   // 50Hz half-period
#define ZCD_OFFSET_US    230     // ZCD falling edge leads true ZC
#define TRIAC_PULSE_US   150     // Gate pulse width
#define MAX_ALPHA_US     3000    // Max firing delay (~60 deg)
#define ALPHA_STEP_US    3       // Resolution step
#define NUM_STEPS        1000    // MAX_ALPHA_US / ALPHA_STEP_US

// ======================== TIMING ========================
#define PID_INTERVAL_MS      500   // PID update rate
#define TEMP_READ_INTERVAL_MS 250  // MAX6675 needs ~220ms conversion
#define PRINT_INTERVAL_MS     1000

// ======================== AUTO-TUNE ========================
#define TUNE_SETPOINT     100.0f  // Tuning test setpoint (C)
#define TUNE_RELAY_POWER  95.0f   // Relay high output (% power)
#define TUNE_HYSTERESIS   0.5f    // Relay deadband (C)
#define TUNE_MIN_CYCLES   6       // Minimum oscillation cycles to record
#define TUNE_MAX_PEAKS    20      // Max peaks/valleys to store

// ======================== EEPROM ========================
#define EEPROM_SIZE       32
#define EEPROM_MAGIC      0xAB
#define ADDR_MAGIC        0
#define ADDR_KP           1
#define ADDR_KI           5
#define ADDR_KD           9
#define ADDR_TU           13
#define ADDR_KU           17

// ======================== TRIAC ISR VARIABLES ========================
static hw_timer_t *triacTimer       = NULL;
static portMUX_TYPE timerMux        = portMUX_INITIALIZER_UNLOCKED;
static volatile uint8_t triacPhase  = 0;   // 0=idle, 1=delay done->fire, 2=pulse on

// Power control (set from main loop, read by ISR)
static volatile uint16_t fireAlphaUs   = MAX_ALPHA_US + 1;  // >MAX = don't fire
static volatile uint16_t burstOn       = 0;     // how many half-cycles to fire
static volatile uint16_t burstTotal    = 20;    // window size (=PID_INTERVAL_MS/10)
static volatile uint16_t burstCount    = 0;     // running counter

// ======================== TEMPERATURE ========================
static float currentTemp           = 0.0f;
static bool  tempValid             = false;
static unsigned long lastTempRead  = 0;

// ======================== PID ========================
static float Kp = 0, Ki = 0, Kd = 0;
static float setpointTemp     = 0;
static float pidOutputPct     = 0;    // 0-100%
static float integral         = 0;
static float prevError        = 0;
static bool  pidActive        = false;
static unsigned long lastPidTime = 0;

// ======================== AUTO-TUNE STATE ========================
enum TuneState { TUNE_IDLE, TUNE_PREHEAT, TUNE_RELAY, TUNE_CALC, TUNE_DONE };
static TuneState tuneState = TUNE_IDLE;
static bool  relayHigh        = false;    // current relay output state
static bool  prevAboveSetpoint = false;
static float tunePeaks[TUNE_MAX_PEAKS];   // temperature peaks
static float tuneValleys[TUNE_MAX_PEAKS]; // temperature valleys
static unsigned long tuneCrossTimes[TUNE_MAX_PEAKS * 2]; // setpoint crossing times
static int   numPeaks     = 0;
static int   numValleys   = 0;
static int   numCrossings = 0;
static float tuneRunningMax = -999;
static float tuneRunningMin = 999;

// ======================== SERIAL ========================
static unsigned long lastPrintTime = 0;
static String serialBuffer = "";

// ================================================================
//                         ISR FUNCTIONS
// ================================================================

// Fast GPIO for IO33
#define TRIAC_HIGH()  digitalWrite(TRIAC_PIN, HIGH)
#define TRIAC_LOW()   digitalWrite(TRIAC_PIN, LOW)

void IRAM_ATTR onZeroCross() {
    portENTER_CRITICAL_ISR(&timerMux);

    // Burst-mode cycle counting
    burstCount++;
    if (burstCount > burstTotal) burstCount = 1;

    bool shouldFire = (burstCount <= burstOn) && (fireAlphaUs <= MAX_ALPHA_US);

    if (shouldFire) {
        triacPhase = 1;
        timerWrite(triacTimer, 0);
        timerAlarmWrite(triacTimer, ZCD_OFFSET_US + fireAlphaUs, false);
        timerAlarmEnable(triacTimer);
    }

    portEXIT_CRITICAL_ISR(&timerMux);
}

void IRAM_ATTR onTriacTimer() {
    portENTER_CRITICAL_ISR(&timerMux);

    if (triacPhase == 1) {
        TRIAC_HIGH();
        triacPhase = 2;
        timerWrite(triacTimer, 0);
        timerAlarmWrite(triacTimer, TRIAC_PULSE_US, false);
        timerAlarmEnable(triacTimer);
    } else if (triacPhase == 2) {
        TRIAC_LOW();
        triacPhase = 0;
        timerAlarmDisable(triacTimer);
    }

    portEXIT_CRITICAL_ISR(&timerMux);
}

// ================================================================
//                       MAX6675 READING
// ================================================================

float readMAX6675() {
    uint16_t raw;

    digitalWrite(MAX6675_CS_PIN, LOW);
    delayMicroseconds(1);
    raw = SPI.transfer16(0x0000);
    digitalWrite(MAX6675_CS_PIN, HIGH);

    if (raw & 0x04) {
        // Thermocouple open / not connected
        return -1.0f;
    }
    return (raw >> 3) * 0.25f;
}

// ================================================================
//                   RMS POWER <-> ALPHA CONVERSION
// ================================================================

// Forward: compute normalised RMS power (0..1) for a given alpha (us).
// For a resistive load with phase-angle control:
//   P/Pmax = (1/pi) * (pi - a + sin(2a)/2)   where a is in radians.
static float powerAtAlpha(float alphaUs) {
    if (alphaUs <= 0) return 1.0f;
    if (alphaUs >= HALF_PERIOD_US) return 0.0f;
    float a = alphaUs / (float)HALF_PERIOD_US * M_PI;  // convert to radians
    return (1.0f / M_PI) * (M_PI - a + sinf(2.0f * a) / 2.0f);
}

// Minimum power achievable with phase control alone (at MAX_ALPHA_US).
static float minPhasePower = 0;  // computed in setup()

// Inverse: find alpha (us) for a desired normalised power (0..1).
// Uses binary search. Returns alpha rounded to ALPHA_STEP_US.
// Returns MAX_ALPHA_US+1 if power cannot be achieved with phase control.
static uint16_t alphaForPower(float powerFrac) {
    if (powerFrac >= 1.0f) return 0;
    if (powerFrac < minPhasePower) return MAX_ALPHA_US + 1;

    float lo = 0, hi = MAX_ALPHA_US;
    for (int i = 0; i < 20; i++) {
        float mid = (lo + hi) * 0.5f;
        float p = powerAtAlpha(mid);
        if (p > powerFrac) lo = mid;
        else                hi = mid;
    }
    float result = (lo + hi) * 0.5f;
    // Round to nearest step
    uint16_t stepped = (uint16_t)(result / ALPHA_STEP_US + 0.5f) * ALPHA_STEP_US;
    if (stepped > MAX_ALPHA_US) stepped = MAX_ALPHA_US;
    return stepped;
}

// ================================================================
//                      SET HEATER POWER
// ================================================================

// powerPct: 0..100 (%)
// Updates the volatile ISR variables for triac firing.
void setPower(float powerPct) {
    powerPct = constrain(powerPct, 0.0f, 100.0f);
    float frac = powerPct / 100.0f;

    uint16_t alpha;
    uint16_t bOn;
    uint16_t bTotal = (uint16_t)(PID_INTERVAL_MS / 10);  // half-cycles in PID window

    if (frac <= 0.001f) {
        // Off
        alpha = MAX_ALPHA_US + 1;
        bOn = 0;
    } else if (frac >= minPhasePower) {
        // Pure phase-angle control
        alpha = alphaForPower(frac);
        bOn = bTotal;  // fire every half-cycle
    } else {
        // Burst mode: fire some half-cycles at MAX_ALPHA to get average power < minPhasePower
        alpha = MAX_ALPHA_US;
        bOn = (uint16_t)(frac / minPhasePower * bTotal + 0.5f);
        if (bOn < 1 && frac > 0) bOn = 1;
        if (bOn > bTotal) bOn = bTotal;
    }

    portENTER_CRITICAL(&timerMux);
    fireAlphaUs = alpha;
    burstOn     = bOn;
    burstTotal  = bTotal;
    portEXIT_CRITICAL(&timerMux);
}

// ================================================================
//                        PID CONTROLLER
// ================================================================

void pidReset() {
    integral  = 0;
    prevError = 0;
    pidOutputPct = 0;
    setPower(0);
}

float pidCompute(float measured, float setpoint, float dt) {
    float error = setpoint - measured;

    integral += error * dt;
    // Anti-windup: clamp integral
    float maxIntegral = (Ki > 0.0001f) ? (100.0f / Ki) : 10000.0f;
    integral = constrain(integral, -maxIntegral, maxIntegral);

    float derivative = (dt > 0.0001f) ? (error - prevError) / dt : 0;
    prevError = error;

    float output = Kp * error + Ki * integral + Kd * derivative;
    return constrain(output, 0.0f, 100.0f);
}

// ================================================================
//                        EEPROM HELPERS
// ================================================================

void eepromWriteFloat(int addr, float val) {
    EEPROM.put(addr, val);
}

float eepromReadFloat(int addr) {
    float val;
    EEPROM.get(addr, val);
    return val;
}

void saveParams() {
    EEPROM.write(ADDR_MAGIC, EEPROM_MAGIC);
    eepromWriteFloat(ADDR_KP, Kp);
    eepromWriteFloat(ADDR_KI, Ki);
    eepromWriteFloat(ADDR_KD, Kd);
    EEPROM.commit();
    Serial.println("[EEPROM] PID parameters saved.");
    Serial.printf("  Kp=%.4f  Ki=%.6f  Kd=%.4f\n", Kp, Ki, Kd);
}

void loadParams() {
    if (EEPROM.read(ADDR_MAGIC) == EEPROM_MAGIC) {
        Kp = eepromReadFloat(ADDR_KP);
        Ki = eepromReadFloat(ADDR_KI);
        Kd = eepromReadFloat(ADDR_KD);
        Serial.println("[EEPROM] PID parameters loaded.");
        Serial.printf("  Kp=%.4f  Ki=%.6f  Kd=%.4f\n", Kp, Ki, Kd);
    } else {
        Serial.println("[EEPROM] No saved parameters found. Run TUNE first.");
    }
}

// ================================================================
//                  ASTROM-HAGGLUND AUTO-TUNE
// ================================================================

void startAutoTune() {
    if (tuneState != TUNE_IDLE) {
        Serial.println("[TUNE] Already running!");
        return;
    }

    Serial.println("===========================================");
    Serial.println("[TUNE] Starting Astrom-Hagglund Relay Feedback");
    Serial.printf("[TUNE] Setpoint = %.1f C\n", TUNE_SETPOINT);
    Serial.printf("[TUNE] Relay power = %.1f %%\n", TUNE_RELAY_POWER);
    Serial.println("===========================================");

    // Reset state
    pidActive = false;
    pidReset();
    numPeaks = 0;
    numValleys = 0;
    numCrossings = 0;
    tuneRunningMax = -999;
    tuneRunningMin = 999;
    relayHigh = true;
    prevAboveSetpoint = false;

    // Start by preheating to close to setpoint
    tuneState = TUNE_PREHEAT;
    setPower(TUNE_RELAY_POWER);
    Serial.println("[TUNE] Preheating to near setpoint...");
}

void runAutoTune() {
    if (tuneState == TUNE_IDLE || tuneState == TUNE_DONE) return;
    if (!tempValid) return;

    float error = currentTemp - TUNE_SETPOINT;
    bool aboveSetpoint = (error > 0);

    switch (tuneState) {

    case TUNE_PREHEAT:
        // Wait until we first reach the setpoint
        if (currentTemp >= TUNE_SETPOINT - TUNE_HYSTERESIS) {
            Serial.println("[TUNE] Reached setpoint. Starting relay oscillation...");
            tuneState = TUNE_RELAY;
            prevAboveSetpoint = false;
            relayHigh = false;
            setPower(0);
            tuneRunningMax = currentTemp;
            tuneRunningMin = currentTemp;
        }
        break;

    case TUNE_RELAY: {
        // Relay control with hysteresis
        if (relayHigh && currentTemp > TUNE_SETPOINT + TUNE_HYSTERESIS) {
            relayHigh = false;
            setPower(0);
        } else if (!relayHigh && currentTemp < TUNE_SETPOINT - TUNE_HYSTERESIS) {
            relayHigh = true;
            setPower(TUNE_RELAY_POWER);
        }

        // Track running max/min for current half-cycle
        if (relayHigh) {
            // Heating phase -> will produce a peak when we switch off
            if (currentTemp > tuneRunningMax) tuneRunningMax = currentTemp;
        } else {
            // Cooling phase -> will produce a valley when we switch on
            if (currentTemp < tuneRunningMin) tuneRunningMin = currentTemp;
        }

        // Detect setpoint crossings
        if (aboveSetpoint != prevAboveSetpoint) {
            unsigned long now = millis();

            if (numCrossings < TUNE_MAX_PEAKS * 2) {
                tuneCrossTimes[numCrossings] = now;
                numCrossings++;
            }

            // When crossing from above to below -> record the valley
            if (!aboveSetpoint && numValleys < TUNE_MAX_PEAKS) {
                tuneValleys[numValleys] = tuneRunningMin;
                numValleys++;
                Serial.printf("[TUNE] Valley #%d: %.2f C\n", numValleys, tuneRunningMin);
                tuneRunningMin = 999;
            }

            // When crossing from below to above -> record the peak
            if (aboveSetpoint && numPeaks < TUNE_MAX_PEAKS) {
                tunePeaks[numPeaks] = tuneRunningMax;
                numPeaks++;
                Serial.printf("[TUNE] Peak #%d: %.2f C\n", numPeaks, tuneRunningMax);
                tuneRunningMax = -999;
            }

            prevAboveSetpoint = aboveSetpoint;

            // Check if we have enough data
            if (numPeaks >= TUNE_MIN_CYCLES && numValleys >= TUNE_MIN_CYCLES) {
                Serial.println("[TUNE] Enough oscillation data collected.");
                tuneState = TUNE_CALC;
            }
        }

        if (prevAboveSetpoint == false && numCrossings == 0) {
            prevAboveSetpoint = aboveSetpoint;
        }
        break;
    }

    case TUNE_CALC:
        finishAutoTune();
        break;

    default:
        break;
    }
}

void finishAutoTune() {
    setPower(0);  // turn off heater

    Serial.println("===========================================");
    Serial.println("[TUNE] Calculating PID parameters...");

    // ---- Compute ultimate period Tu ----
    // Tu = average full-cycle period.  Two consecutive same-direction crossings = one cycle.
    // We use every other crossing (same direction).
    float sumPeriod = 0;
    int periodCount = 0;
    for (int i = 2; i < numCrossings; i += 2) {
        float period = (tuneCrossTimes[i] - tuneCrossTimes[i - 2]) / 1000.0f; // seconds
        sumPeriod += period;
        periodCount++;
    }
    float Tu = (periodCount > 0) ? sumPeriod / periodCount : 0;

    // ---- Compute oscillation amplitude a ----
    // a = average of (peak - valley) / 2, skipping the first cycle (transient)
    int skip = 1;  // skip first peak/valley as transient
    float sumAmp = 0;
    int ampCount = 0;
    int minCount = min(numPeaks, numValleys);
    for (int i = skip; i < minCount; i++) {
        float amp = (tunePeaks[i] - tuneValleys[i]) / 2.0f;
        sumAmp += amp;
        ampCount++;
    }
    float a = (ampCount > 0) ? sumAmp / ampCount : 0;

    Serial.printf("[TUNE] Ultimate period Tu = %.2f s\n", Tu);
    Serial.printf("[TUNE] Oscillation amplitude a = %.2f C\n", a);

    if (Tu < 0.1f || a < 0.01f) {
        Serial.println("[TUNE] ERROR: Invalid oscillation data. Tune failed.");
        tuneState = TUNE_DONE;
        return;
    }

    // ---- Ultimate gain Ku ----
    // Relay amplitude d = TUNE_RELAY_POWER / 2  (relay swings between 0 and TUNE_RELAY_POWER)
    float d = TUNE_RELAY_POWER / 2.0f;
    float Ku = (4.0f * d) / (M_PI * a);

    Serial.printf("[TUNE] Relay amplitude d = %.2f\n", d);
    Serial.printf("[TUNE] Ultimate gain Ku = %.4f\n", Ku);

    // ---- Tyreus-Luyben tuning ----
    //   Kp = Ku / 2.2
    //   Ti = 2.2 * Tu
    //   Td = Tu / 6.3
    //   Ki = Kp / Ti
    //   Kd = Kp * Td
    float TL_Kp = Ku / 2.2f;
    float TL_Ti = 2.2f * Tu;
    float TL_Td = Tu / 6.3f;
    float TL_Ki = TL_Kp / TL_Ti;
    float TL_Kd = TL_Kp * TL_Td;

    Serial.println("-------------------------------------------");
    Serial.println("[TUNE] Tyreus-Luyben PID Parameters:");
    Serial.printf("  Kp = %.4f\n", TL_Kp);
    Serial.printf("  Ki = %.6f\n", TL_Ki);
    Serial.printf("  Kd = %.4f\n", TL_Kd);
    Serial.printf("  Ti = %.2f s\n", TL_Ti);
    Serial.printf("  Td = %.2f s\n", TL_Td);
    Serial.println("-------------------------------------------");

    // Apply and save
    Kp = TL_Kp;
    Ki = TL_Ki;
    Kd = TL_Kd;

    // Also save Tu and Ku for reference
    eepromWriteFloat(ADDR_TU, Tu);
    eepromWriteFloat(ADDR_KU, Ku);
    saveParams();

    Serial.println("[TUNE] Complete! Parameters saved to EEPROM.");
    Serial.println("[TUNE] You can now use SET <temp> to control temperature.");
    Serial.println("===========================================");

    tuneState = TUNE_DONE;
}

// ================================================================
//                    SERIAL COMMAND PARSER
// ================================================================

void processSerial() {
    while (Serial.available()) {
        char c = Serial.read();
        if (c == '\n' || c == '\r') {
            serialBuffer.trim();
            if (serialBuffer.length() == 0) {
                serialBuffer = "";
                continue;
            }

            Serial.printf("> %s\n", serialBuffer.c_str());

            if (serialBuffer.equalsIgnoreCase("TUNE")) {
                startAutoTune();
            }
            else if (serialBuffer.startsWith("SET") || serialBuffer.startsWith("set")) {
                // Parse temperature from "SET 150" or just "SET" then prompt
                String arg = serialBuffer.substring(3);
                arg.trim();

                if (arg.length() > 0) {
                    float temp = arg.toFloat();
                    if (temp >= 20.0f && temp <= 200.0f) {
                        setpointTemp = temp;
                        pidActive = true;
                        pidReset();
                        tuneState = TUNE_IDLE;
                        Serial.printf("[PID] Setpoint = %.1f C. PID control active.\n", setpointTemp);
                        if (Kp < 0.0001f && Ki < 0.0001f && Kd < 0.0001f) {
                            Serial.println("[PID] WARNING: PID parameters are zero. Run TUNE first!");
                        }
                    } else {
                        Serial.println("[SET] Temperature must be between 20 and 200 C.");
                    }
                } else {
                    Serial.println("[SET] Enter temperature (20-200 C):");
                }
            }
            else if (serialBuffer.equalsIgnoreCase("STOP")) {
                pidActive = false;
                tuneState = TUNE_IDLE;
                setPower(0);
                pidReset();
                Serial.println("[CTRL] Heater OFF. Control stopped.");
            }
            else if (serialBuffer.equalsIgnoreCase("STATUS")) {
                Serial.println("------- STATUS -------");
                Serial.printf("  Temp     = %.2f C\n", currentTemp);
                Serial.printf("  Setpoint = %.1f C\n", setpointTemp);
                Serial.printf("  PID Out  = %.1f %%\n", pidOutputPct);
                Serial.printf("  Alpha    = %d us\n", fireAlphaUs);
                Serial.printf("  Burst    = %d/%d\n", burstOn, burstTotal);
                Serial.printf("  Kp=%.4f Ki=%.6f Kd=%.4f\n", Kp, Ki, Kd);
                Serial.printf("  PID active: %s\n", pidActive ? "YES" : "NO");
                Serial.printf("  Tune state: %d\n", tuneState);
                Serial.println("----------------------");
            }
            else {
                // Try to parse as a temperature value (for SET prompt)
                float temp = serialBuffer.toFloat();
                if (temp >= 20.0f && temp <= 200.0f) {
                    setpointTemp = temp;
                    pidActive = true;
                    pidReset();
                    tuneState = TUNE_IDLE;
                    Serial.printf("[PID] Setpoint = %.1f C. PID control active.\n", setpointTemp);
                    if (Kp < 0.0001f && Ki < 0.0001f && Kd < 0.0001f) {
                        Serial.println("[PID] WARNING: PID parameters are zero. Run TUNE first!");
                    }
                } else {
                    Serial.println("[CMD] Unknown command. Available: TUNE, SET <temp>, STOP, STATUS");
                }
            }

            serialBuffer = "";
        } else {
            serialBuffer += c;
        }
    }
}

// ================================================================
//                         SETUP & LOOP
// ================================================================

void setup() {
    Serial.begin(115200);
    delay(500);
    Serial.println();
    Serial.println("=========================================");
    Serial.println("  Filament Dryer Controller v1.0");
    Serial.println("  ESP32 + Triac Phase Control + MAX6675");
    Serial.println("=========================================");

    // --- Pins ---
    pinMode(TRIAC_PIN, OUTPUT);
    digitalWrite(TRIAC_PIN, LOW);
    pinMode(ZCD_PIN, INPUT);           // IO34 is input-only
    pinMode(MAX6675_CS_PIN, OUTPUT);
    digitalWrite(MAX6675_CS_PIN, HIGH);

    // --- SPI (VSPI) for MAX6675 ---
    SPI.begin();  // default VSPI: SCK=18, MISO=19, MOSI=23

    // --- EEPROM ---
    EEPROM.begin(EEPROM_SIZE);
    loadParams();

    // --- Precompute min phase power ---
    minPhasePower = powerAtAlpha((float)MAX_ALPHA_US);
    Serial.printf("[INFO] Min phase-control power = %.1f %%\n", minPhasePower * 100.0f);
    Serial.printf("[INFO] Phase control range: %.1f%% - 100%%\n", minPhasePower * 100.0f);
    Serial.printf("[INFO] Below %.1f%%: burst/cycle-skip mode\n", minPhasePower * 100.0f);

    // --- Hardware timer for triac (timer 0, prescaler 80 -> 1us tick) ---
    triacTimer = timerBegin(0, 80, true);           // timer 0, div 80, count up
    timerAttachInterrupt(triacTimer, &onTriacTimer, true);  // edge trigger
    timerAlarmDisable(triacTimer);

    // --- Zero-cross interrupt (falling edge) ---
    attachInterrupt(digitalPinToInterrupt(ZCD_PIN), onZeroCross, FALLING);

    // --- Initial temperature read ---
    delay(300);
    currentTemp = readMAX6675();
    if (currentTemp < 0) {
        Serial.println("[WARN] Thermocouple not detected! Check wiring.");
        tempValid = false;
    } else {
        tempValid = true;
        Serial.printf("[INFO] Initial temperature: %.2f C\n", currentTemp);
    }

    Serial.println();
    Serial.println("Commands:");
    Serial.println("  TUNE        - Auto-tune PID (Astrom-Hagglund + Tyreus-Luyben)");
    Serial.println("  SET <temp>  - Set target temperature (20-200 C)");
    Serial.println("  STOP        - Stop heater and PID");
    Serial.println("  STATUS      - Print current state");
    Serial.println();

    lastTempRead = millis();
    lastPidTime  = millis();
    lastPrintTime = millis();
}

void loop() {
    unsigned long now = millis();

    // ---- Read temperature ----
    if (now - lastTempRead >= TEMP_READ_INTERVAL_MS) {
        lastTempRead = now;
        float t = readMAX6675();
        if (t >= 0) {
            currentTemp = t;
            tempValid = true;
        } else {
            tempValid = false;
        }
    }

    // ---- PID control ----
    if (pidActive && tempValid && (now - lastPidTime >= PID_INTERVAL_MS)) {
        float dt = (now - lastPidTime) / 1000.0f;
        lastPidTime = now;

        pidOutputPct = pidCompute(currentTemp, setpointTemp, dt);
        setPower(pidOutputPct);
    }

    // ---- Auto-tune state machine ----
    if (tuneState != TUNE_IDLE && tuneState != TUNE_DONE) {
        runAutoTune();
    }

    // ---- Serial printing ----
    if (now - lastPrintTime >= PRINT_INTERVAL_MS) {
        lastPrintTime = now;

        if (tempValid) {
            Serial.printf("T=%.2f C", currentTemp);
        } else {
            Serial.print("T=ERR (open TC)");
        }

        if (pidActive) {
            Serial.printf(" | SP=%.1f C | PID=%.1f%% | a=%d us | burst=%d/%d",
                          setpointTemp, pidOutputPct, fireAlphaUs, burstOn, burstTotal);
        }

        if (tuneState == TUNE_PREHEAT) {
            Serial.print(" | [TUNING: preheat]");
        } else if (tuneState == TUNE_RELAY) {
            Serial.printf(" | [TUNING: relay %s, peaks=%d valleys=%d]",
                          relayHigh ? "ON" : "OFF", numPeaks, numValleys);
        }

        Serial.println();
    }

    // ---- Serial commands ----
    processSerial();
}
