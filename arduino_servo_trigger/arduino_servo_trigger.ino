/*
  TVAM servo trigger board  (Arduino Uno / Nano, ATmega328P @ 16 MHz)

  Turns the encoder output of the Delta ASD-E3-0221-L drive into DMD triggers.
    OA : one rising edge per DMD frame (drive parameter P1.046 = frames per turn)
    Z  : once per turn, marks angle 0. Printing starts on the first Z after arming.

  Wiring (see docs/servo_wiring/README.md)
    D2  <- Z.  Default: CN1 pin 44 (OCZ, open collector, active LOW) with a
               1-2.2 kOhm pull-up to 5 V.  If you feed OZ through an AM26C32
               instead, the signal is active HIGH -> use zpol = 1.
    D3  <- OA. CN1 pin 21 directly (single-ended) or the AM26C32 output.
    D5  -> DMD trigger input (same pin as the old AND-gate board).
    A0  -> HIGH while frames are being sent (like the old VIBRATION_PIN).
    GND <-> CN1 pin 29 and pin 40 (drive GND).

  Noise protection
    - An OA high must last FILTER_SAMPLES loop passes (~3-4 us) to count.
    - After an accepted edge, further edges are ignored for the lockout time
      (the PC sets it to half a frame period). A single noise spike therefore
      cannot add an extra frame: at worst it shifts one frame slightly early.
    - Every rejected edge / short spike is counted and reported, so you can
      see whether noise is reaching the board.

  Serial protocol: 115200 baud, one command per line.
    ?                                  -> "TVAM-SERVO 1"
    S <fpr> <lock_us> <pulse_us> <zpol> -> "OK"   frames per turn, lockout,
                                          output pulse width, Z polarity
                                          (0 = active low / OCZ, 1 = active high)
    C <turns>   count only, DMD is NOT triggered. Measures OA edges per turn.
    A <frames>  print: wait for Z, then send <frames> triggers to the DMD.
  Any byte received while C or A is running aborts it.
  C and A both answer with
    REV <i> <count>      one line per completed turn (first MAX_REVS turns)
    RESULT <sent> <turns> <rejected> <spikes> <status>
  status: OK | ABORT | NOZ (no Z pulse within ~60 s) | NOOA (OA stopped for ~2 s)
*/

#include <Arduino.h>

#define Z_BIT     _BV(PD2)   // D2
#define OA_BIT    _BV(PD3)   // D3
#define OUT_BIT   _BV(PD5)   // D5
#define GATE_BIT  _BV(PC0)   // A0

const uint8_t  FILTER_SAMPLES = 3;
const uint16_t MAX_REVS = 100;
const uint16_t TIMEOUT_OVF = 61;        // OA timeout: Timer1 overflows (32.768 ms each) ~ 2 s
const uint16_t TIMEOUT_Z_OVF = 1831;    // waiting for the first Z: ~60 s (slow turns)

uint32_t framesPerRev = 1000;
uint16_t lockTicks = 1000;              // Timer1 ticks are 0.5 us
uint16_t pulseTicks = 20;
uint8_t  zActiveVal = 0;                // value of (PIND & Z_BIT) when Z is active

uint32_t revCounts[MAX_REVS];

static inline bool zActive(uint8_t pins) { return (pins & Z_BIT) == zActiveVal; }

void setup() {
  DDRD |= OUT_BIT;  PORTD &= ~OUT_BIT;
  DDRC |= GATE_BIT; PORTC &= ~GATE_BIT;
  pinMode(2, INPUT_PULLUP);   // weak pull-ups only keep open inputs quiet;
  pinMode(3, INPUT_PULLUP);   // OCZ still needs the external 1-2.2 kOhm pull-up
  Serial.begin(115200);
  Serial.setTimeout(200);
}

// Main gate. driveOut = false only counts (used for the self-check).
void runGate(bool driveOut, uint32_t maxFrames, uint16_t maxRevs) {
  uint32_t sent = 0, rejected = 0, spikes = 0, revCount = 0;
  uint16_t revs = 0, ovf = 0, tEdge = 0;
  uint8_t highRun = 0;
  bool armed = false, locked = false, outHigh = false, zPrev = true;
  const uint32_t minRevCount = framesPerRev / 2;   // ignores Z glitches
  const char *status = "OK";

  noInterrupts();
  TCCR1A = 0;
  TCCR1B = _BV(CS11);           // prescaler 8 -> 0.5 us ticks
  TCNT1 = 0;
  TIFR1 = _BV(TOV1);

  // 1) wait for the start of a Z pulse = angle 0
  for (;;) {
    bool z = zActive(PIND);
    if (z && !zPrev) break;
    zPrev = z;
    if (TIFR1 & _BV(TOV1)) { TIFR1 = _BV(TOV1); if (++ovf > TIMEOUT_Z_OVF) { status = "NOZ"; goto done; } }
    if (UCSR0A & _BV(RXC0)) { status = "ABORT"; goto done; }
  }

  // 2) forward OA rising edges
  PORTC |= GATE_BIT;
  armed = !(PIND & OA_BIT);     // if OA is already high, that edge came before Z
  zPrev = true;                 // we are inside the Z pulse that started the run
  ovf = 0;
  for (;;) {
    uint8_t p = PIND;
    uint16_t now = TCNT1;

    if (outHigh && (uint16_t)(now - tEdge) >= pulseTicks) { PORTD &= ~OUT_BIT; outHigh = false; }
    if (locked && (uint16_t)(now - tEdge) >= lockTicks) locked = false;

    if (p & OA_BIT) {
      if (armed && ++highRun >= FILTER_SAMPLES) {
        armed = false;
        highRun = 0;
        if (!locked) {
          if (driveOut) { PORTD |= OUT_BIT; outHigh = true; }
          tEdge = now;
          locked = true;
          ovf = 0;
          ++sent;
          ++revCount;
          if (sent >= maxFrames) {
            while ((uint16_t)(TCNT1 - tEdge) < pulseTicks) {}   // finish last pulse
            break;
          }
        } else {
          ++rejected;           // edge inside lockout window -> noise
        }
      }
    } else {
      if (highRun) { ++spikes; highRun = 0; }   // high too short -> noise
      armed = true;
    }

    bool z = zActive(p);
    if (z && !zPrev && revCount >= minRevCount) {
      if (revs < MAX_REVS) revCounts[revs] = revCount;
      ++revs;
      revCount = 0;
      if (revs >= maxRevs) break;
    }
    zPrev = z;

    if (TIFR1 & _BV(TOV1)) { TIFR1 = _BV(TOV1); if (++ovf > TIMEOUT_OVF) { status = "NOOA"; break; } }
    if (UCSR0A & _BV(RXC0)) { status = "ABORT"; break; }
  }

done:
  PORTD &= ~OUT_BIT;
  PORTC &= ~GATE_BIT;
  TCCR1B = 0;
  interrupts();

  delay(5);
  while (Serial.available()) Serial.read();   // drop the abort byte

  uint16_t n = revs < MAX_REVS ? revs : MAX_REVS;
  for (uint16_t i = 0; i < n; ++i) {
    Serial.print(F("REV ")); Serial.print(i); Serial.print(' '); Serial.println(revCounts[i]);
  }
  Serial.print(F("RESULT ")); Serial.print(sent); Serial.print(' ');
  Serial.print(revs); Serial.print(' '); Serial.print(rejected); Serial.print(' ');
  Serial.print(spikes); Serial.print(' '); Serial.println(status);
}

void loop() {
  if (!Serial.available()) return;
  String line = Serial.readStringUntil('\n');
  line.trim();
  if (line.length() == 0) return;

  char cmd = line.charAt(0);
  long v[4] = {0, 0, 0, 0};
  sscanf(line.c_str() + 1, "%ld %ld %ld %ld", &v[0], &v[1], &v[2], &v[3]);

  if (cmd == '?') {
    Serial.println(F("TVAM-SERVO 1"));
  } else if (cmd == 'S') {
    if (v[0] < 1 || v[1] < 1 || v[2] < 1) { Serial.println(F("ERR bad S arguments")); return; }
    framesPerRev = (uint32_t)v[0];
    long lock = v[1] * 2L;  if (lock > 60000L) lock = 60000L;    // max 30 ms
    long pulse = v[2] * 2L; if (pulse >= lock) pulse = lock / 2;
    if (pulse < 2) pulse = 2;
    lockTicks = (uint16_t)lock;
    pulseTicks = (uint16_t)pulse;
    zActiveVal = v[3] ? Z_BIT : 0;
    Serial.println(F("OK"));
  } else if (cmd == 'C') {
    if (v[0] < 1) v[0] = 1;
    runGate(false, 0xFFFFFFFFUL, (uint16_t)min(v[0], 65000L));
  } else if (cmd == 'A') {
    if (v[0] < 1) { Serial.println(F("ERR bad A arguments")); return; }
    runGate(true, (uint32_t)v[0], 0xFFFF);
  } else {
    Serial.println(F("ERR unknown command"));
  }
}
