/*
This script outputs a signal if both input signal are on at the same time. 
Additionally it displayes the current inputs and outputs everytime a change occurs.
*/

const int inputPin1 = 2;  // Define the pin for the first input signal
const int inputPin2 = 3;  // Define the pin for the second input signal
// tvam laser pin 13
const int outputPin = 13; // Define the pin for the output signal 


const int VIBRATION_PIN = A0;


void setup() {
  pinMode(inputPin1, INPUT);  // Set the first input pin as an input
  pinMode(inputPin2, INPUT);  // Set the second input pin as an input
  pinMode(outputPin, OUTPUT); // Set the output pin as an output
  pinMode(VIBRATION_PIN, OUTPUT); // Set the output pin as an output

  Serial.begin(9600); // Start serial communication at 9600 baud
}


void loop() {

  int signal1 = digitalRead(inputPin1); // Read the state of the first input signal
  int signal2 = digitalRead(inputPin2); // Read the state of the second input signal

  int signal1_before = 0;
  int signal2_before = 0;

  while(true){
    signal1 = digitalRead(inputPin1); // Read the state of the first input signal
    signal2 = digitalRead(inputPin2); // Read the state of the second input signal

    if (signal2 == HIGH){
        digitalWrite(VIBRATION_PIN, HIGH); // Power on A0
    } else {
        digitalWrite(VIBRATION_PIN, LOW); // Power off
    }
      
    
    if (signal1 == HIGH && signal2 == HIGH) { // Check if both input signals are on
      digitalWrite(outputPin, HIGH);
    } else {
      digitalWrite(outputPin, LOW);
    }
  }
}

