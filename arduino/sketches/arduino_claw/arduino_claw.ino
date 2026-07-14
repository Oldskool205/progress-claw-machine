#include <IBusBM.h>

IBusBM ibus;

// ================== Remote Channels ==================
int rcCH1;
int rcCH2;
int rcCH3;
int rcCH4;
bool rcCH5;
bool rcCH6;

// ================== Button Inputs ==================
#define up1Pin    2
#define down1Pin  3

#define buzzerPin 4

#define step1Pin  6
#define dir1Pin   7

#define up2Pin    8
#define down2Pin  9

#define step2Pin  11
#define dir2Pin   12

#define linearUpRelayPin   10
#define linearDownRelayPin 13

#define xHomePin A4
#define yHomePin A5

#define grabberPin 5
#define dashboardStartPin A0
#define grabberPowerBit0Pin A1
#define grabberPowerBit1Pin A2
#define grabberPowerBit2Pin A3

// ================== Variables ==================
int speedDelay = 750;
int deadZone = 25;
const byte grabberPulsePwmValue = 255;
const byte grabberPowerMinimumPercent = 40;
const byte grabberPowerStepPercent = 10;
const byte timeUpGrabberPulseCode = 7;
const byte linearStopped = 0;
const byte linearMovingUp = 1;
const byte linearMovingDown = 2;
const byte homingIdle = 0;
const byte homingYAxis = 1;
const byte homingXAxis = 2;
const byte homingComplete = 3;
const byte homingFault = 4;

// Change either level if an axis moves away from its home switch. Motor 2 is X
// and Motor 1 is Y in this machine.
const byte xHomeDirection = LOW;
const byte yHomeDirection = HIGH;
const bool xHomingEnabled = false;
const int homingSpeedDelay = 1000;
const unsigned long yHomingTimeout = 60000;
const unsigned long xHomingTimeout = 30000;
const unsigned long homingBuzzerInterval = 150;

bool moving = false;
byte linearMotorState = linearStopped;
bool dashboardPlayActive = false;
bool previousDashboardStart = HIGH;
unsigned long dashboardPlayStarted = 0;
const unsigned long dashboardPlayDuration = 180000;
const unsigned long grabberPulseInterval = 1000;
const byte grabberPulseToggleCount = 6;

bool grabberPulseActive = false;
bool timeUpGrabberPulseActive = false;
bool grabberPulseState = false;
byte grabberPulseToggles = 0;
unsigned long lastGrabberPulse = 0;

unsigned long lastBeep = 0;
bool beepState = false;

byte homingState = homingIdle;
unsigned long homingAxisStarted = 0;
unsigned long lastHomingBeep = 0;

// =====================================================

int readChannel(byte channelInput, int minLimit, int maxLimit, int defaultValue) {

  uint16_t ch = ibus.readChannel(channelInput);

  if (ch < 100) {
    return defaultValue;
  }

  return map(ch, 1000, 2000, minLimit, maxLimit);
}

bool readSwitch(byte channelInput, bool defaultValue) {

  int intDefaultValue = defaultValue ? 100 : 0;

  int ch = readChannel(channelInput, 0, 100, intDefaultValue);

  return (ch > 50);
}

// =====================================================

void setup() {

  pinMode(step1Pin, OUTPUT);
  pinMode(dir1Pin, OUTPUT);

  pinMode(step2Pin, OUTPUT);
  pinMode(dir2Pin, OUTPUT);

  pinMode(linearUpRelayPin, OUTPUT);
  pinMode(linearDownRelayPin, OUTPUT);

  // Normally-closed switches: LOW is healthy/not triggered. HIGH means the
  // home position was reached or the switch wiring is disconnected.
  pinMode(xHomePin, INPUT_PULLUP);
  pinMode(yHomePin, INPUT_PULLUP);

  pinMode(grabberPin, OUTPUT);

  pinMode(up1Pin, INPUT_PULLUP);
  pinMode(down1Pin, INPUT_PULLUP);

  pinMode(up2Pin, INPUT_PULLUP);
  pinMode(down2Pin, INPUT_PULLUP);

  pinMode(buzzerPin, OUTPUT);
  pinMode(dashboardStartPin, INPUT_PULLUP);
  pinMode(grabberPowerBit0Pin, INPUT);
  pinMode(grabberPowerBit1Pin, INPUT);
  pinMode(grabberPowerBit2Pin, INPUT);

  digitalWrite(buzzerPin, LOW);
  linearStop();
  setGrabberOutput(false);

  Serial.begin(115200);

  ibus.begin(Serial);
}

// =====================================================

void loop() {

  moving = false;

  // ================== Read Remote ==================

  rcCH1 = readChannel(0, -100, 100, 0);
  rcCH2 = readChannel(1, -100, 100, 0);
  rcCH3 = readChannel(2, 0, 100, 50);
  rcCH4 = readChannel(3, -100, 100, 0);

  rcCH5 = readSwitch(4, false);
  rcCH6 = readSwitch(5, false);

  // The Raspberry Pi holds A0 low during a test or play. Releasing A0 stops
  // immediately. The timer is a safety limit if the dashboard fails to stop.
  bool dashboardStart = digitalRead(dashboardStartPin);
  if (
    previousDashboardStart == HIGH &&
    dashboardStart == LOW &&
    homingState != homingFault
  ) {
    // Reserved power code 111 plus a new active-low gate pulse is a dedicated
    // dashboard homing request. Normal games use levels 000 through 110.
    if (readGrabberPowerLevel() == timeUpGrabberPulseCode) {
      dashboardPlayActive = false;
      startHoming();
    }
    else {
      dashboardPlayActive = true;
      dashboardPlayStarted = millis();
      startGrabberPulse();
    }
  }

  if (
    dashboardPlayActive &&
    (
      dashboardStart == HIGH ||
      millis() - dashboardPlayStarted >= dashboardPlayDuration
    )
  ) {
    if (dashboardStart == HIGH && readGrabberPowerLevel() == timeUpGrabberPulseCode) {
      startTimeUpGrabberPulse();
    }
    dashboardPlayActive = false;
    startHoming();
  }
  previousDashboardStart = dashboardStart;

  // The dashboard is the hard safety gate for the machine. Opening the
  // dashboard leaves the machine disabled; Start enables it, and Stop or the
  // timeout disables it. CH6 is still read but cannot bypass this gate.

  // Stop all Arduino-generated outputs and ignore the FlySky receiver and
  // physical movement buttons whenever the dashboard gate is closed.
  if (!dashboardPlayActive) {
    digitalWrite(step1Pin, LOW);
    digitalWrite(step2Pin, LOW);
    linearStop();

    if (timeUpGrabberPulseActive) {
      digitalWrite(buzzerPin, LOW);
      beepState = false;
      updateGrabberPulse();
      return;
    }

    if (homingState != homingIdle) {
      updateHoming();
      return;
    }

    digitalWrite(buzzerPin, LOW);
    beepState = false;
    setGrabberOutput(false);
    grabberPulseActive = false;
    grabberPulseState = false;
    grabberPulseToggles = 0;
    return;
  }

  if (updateGrabberPulse()) {
    return;
  }

  // CH6 = Grabber on/off on PWM pin 5. The dashboard selects grabber hold
  // strength with A1/A2/A3. The dashboard play gate still forces the grabber
  // off immediately when stopped or timed out.
  setGrabberOutput(rcCH6);

  // CH3 = Speed Control
  speedDelay = map(rcCH3, 0, 100, 1200, 200);

  // ================== Read Buttons ==================

  bool up1Pressed   = digitalRead(up1Pin) == LOW;
  bool down1Pressed = digitalRead(down1Pin) == LOW;

  bool up2Pressed   = digitalRead(up2Pin) == LOW;
  bool down2Pressed = digitalRead(down2Pin) == LOW;

  // ==================================================
  // BUTTON CONTROL
  // ==================================================

  if (up1Pressed && !down1Pressed) {

    digitalWrite(dir1Pin, HIGH);
    moveStepper(step1Pin, speedDelay);
    moving = true;
  }
  else if (down1Pressed && !up1Pressed) {

    digitalWrite(dir1Pin, LOW);
    moveStepper(step1Pin, speedDelay);
    moving = true;
  }

  if (up2Pressed && !down2Pressed) {

    digitalWrite(dir2Pin, HIGH);
    moveStepper(step2Pin, speedDelay);
    moving = true;
  }
  else if (down2Pressed && !up2Pressed) {

    digitalWrite(dir2Pin, LOW);
    moveStepper(step2Pin, speedDelay);
    moving = true;
  }

  // ==================================================
  // REMOTE CONTROL (CH5 ON)
  // ==================================================

  if (rcCH5) {

    // CH1 -> Motor 2 (X)

    if (rcCH1 > deadZone) {

      digitalWrite(dir2Pin, HIGH);
      moveStepper(step2Pin, speedDelay);
      moving = true;
    }
    else if (rcCH1 < -deadZone) {

      digitalWrite(dir2Pin, LOW);
      moveStepper(step2Pin, speedDelay);
      moving = true;
    }

    // CH2 -> Motor 1 (Y)

    if (rcCH2 > deadZone) {

      digitalWrite(dir1Pin, LOW);
      moveStepper(step1Pin, speedDelay);
      moving = true;
    }
    else if (rcCH2 < -deadZone) {

      digitalWrite(dir1Pin, HIGH);
      moveStepper(step1Pin, speedDelay);
      moving = true;
    }

    // CH4 -> 24 VDC linear actuator relay control

    if (rcCH4 > deadZone) {
      linearUp();
      moving = true;
    }
    else if (rcCH4 < -deadZone) {
      linearDown();
      moving = true;
    }
    else {
      linearStop();
    }
  }
  else {
    linearStop();
  }

  // ==================================================
  // BUZZER
  // ==================================================

  if (moving) {

    if (millis() - lastBeep > 300) {

      lastBeep = millis();

      beepState = !beepState;

      digitalWrite(buzzerPin, beepState);
    }
  }
  else {

    digitalWrite(buzzerPin, LOW);
  }
}

// =====================================================

void moveStepper(int stepPin, int delayTime) {

  digitalWrite(stepPin, HIGH);
  delayMicroseconds(delayTime);

  digitalWrite(stepPin, LOW);
  delayMicroseconds(delayTime);
}

bool xHomeActive() {
  return digitalRead(xHomePin) == HIGH;
}

bool yHomeActive() {
  return digitalRead(yHomePin) == HIGH;
}

void startHoming() {
  digitalWrite(step1Pin, LOW);
  digitalWrite(step2Pin, LOW);
  linearStop();
  setGrabberOutput(false);

  homingState = homingYAxis;
  homingAxisStarted = millis();
  lastHomingBeep = millis();
  beepState = true;
  digitalWrite(buzzerPin, HIGH);
}

void updateHoming() {
  if (millis() - lastHomingBeep >= homingBuzzerInterval) {
    lastHomingBeep = millis();
    beepState = !beepState;
    digitalWrite(buzzerPin, beepState);
  }

  if (homingState == homingYAxis) {
    if (yHomeActive()) {
      digitalWrite(step1Pin, LOW);
      if (xHomingEnabled) {
        homingState = homingXAxis;
        homingAxisStarted = millis();
      }
      else {
        homingState = homingComplete;
      }
      return;
    }

    if (millis() - homingAxisStarted >= yHomingTimeout) {
      stopHomingWithFault();
      return;
    }

    digitalWrite(dir1Pin, yHomeDirection);
    moveStepper(step1Pin, homingSpeedDelay);
    return;
  }

  if (homingState == homingXAxis) {
    if (xHomeActive()) {
      digitalWrite(step2Pin, LOW);
      homingState = homingComplete;
    }
    else if (millis() - homingAxisStarted >= xHomingTimeout) {
      stopHomingWithFault();
      return;
    }
    else {
      digitalWrite(dir2Pin, xHomeDirection);
      moveStepper(step2Pin, homingSpeedDelay);
      return;
    }
  }

  if (homingState == homingComplete) {
    digitalWrite(step1Pin, LOW);
    digitalWrite(step2Pin, LOW);
    digitalWrite(buzzerPin, LOW);
    beepState = false;
    homingState = homingIdle;
  }
}

void stopHomingWithFault() {
  digitalWrite(step1Pin, LOW);
  digitalWrite(step2Pin, LOW);
  digitalWrite(buzzerPin, HIGH);
  beepState = true;
  homingState = homingFault;
}

void linearStop() {
  digitalWrite(linearUpRelayPin, LOW);
  digitalWrite(linearDownRelayPin, LOW);
  linearMotorState = linearStopped;
}

void linearUp() {
  if (linearMotorState == linearMovingUp) {
    return;
  }

  digitalWrite(linearDownRelayPin, LOW);
  delay(50);
  digitalWrite(linearUpRelayPin, HIGH);
  linearMotorState = linearMovingUp;
}

void linearDown() {
  if (linearMotorState == linearMovingDown) {
    return;
  }

  digitalWrite(linearUpRelayPin, LOW);
  delay(50);
  digitalWrite(linearDownRelayPin, HIGH);
  linearMotorState = linearMovingDown;
}

void setGrabberOutput(bool enabled) {
  analogWrite(grabberPin, enabled ? readGrabberHoldPwmValue() : 0);
}

void setGrabberPulseOutput(bool enabled) {
  analogWrite(grabberPin, enabled ? grabberPulsePwmValue : 0);
}

byte readGrabberHoldPwmValue() {
  byte level = readGrabberPowerLevel();
  byte percent = grabberPowerMinimumPercent + (level * grabberPowerStepPercent);
  if (percent > 100) {
    percent = 100;
  }

  return map(percent, 0, 100, 0, 255);
}

byte readGrabberPowerLevel() {
  byte level = 0;

  if (digitalRead(grabberPowerBit0Pin) == HIGH) {
    level |= 1;
  }
  if (digitalRead(grabberPowerBit1Pin) == HIGH) {
    level |= 2;
  }
  if (digitalRead(grabberPowerBit2Pin) == HIGH) {
    level |= 4;
  }

  return level;
}

void startGrabberPulse() {
  grabberPulseActive = true;
  timeUpGrabberPulseActive = false;
  grabberPulseState = true;
  grabberPulseToggles = 1;
  lastGrabberPulse = millis();
  setGrabberPulseOutput(true);
}

void startTimeUpGrabberPulse() {
  grabberPulseActive = true;
  timeUpGrabberPulseActive = true;
  grabberPulseState = true;
  grabberPulseToggles = 1;
  lastGrabberPulse = millis();
  setGrabberPulseOutput(true);
}

bool updateGrabberPulse() {
  if (!grabberPulseActive) {
    return false;
  }

  if (millis() - lastGrabberPulse >= grabberPulseInterval) {
    lastGrabberPulse = millis();
    grabberPulseState = !grabberPulseState;
    grabberPulseToggles++;
    setGrabberPulseOutput(grabberPulseState);

    if (grabberPulseToggles >= grabberPulseToggleCount) {
      grabberPulseActive = false;
      timeUpGrabberPulseActive = false;
      grabberPulseState = false;
      setGrabberOutput(false);
    }
  }

  return grabberPulseActive;
}
