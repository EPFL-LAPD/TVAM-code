const int inputPin1 = 2;  // Define the pin for the first input signal
const int inputPin2 = 3;  // Define the pin for the second input signal
const int outputPin = 13; // Define the pin for the output signal 
void setup() {
  pinMode(inputPin1, INPUT);  // Set the first input pin as an input
  pinMode(inputPin2, INPUT);  // Set the second input pin as an input
  pinMode(outputPin, OUTPUT); // Set the output pin as an output
  Serial.begin(9600); // Start serial communication at 9600 baud
}


void loop() {

  int signal1 = digitalRead(inputPin1); // Read the state of the first input signal
  int signal2 = digitalRead(inputPin2); // Read the state of the second input signal
  int signal3 = 0;

  int signal1_before = 0;
  int signal2_before = 0;
  int signal3_before = 0; 

  while(true){
    signal1 = digitalRead(inputPin1); // Read the state of the first input signal
    signal2 = digitalRead(inputPin2); // Read the state of the second input signal
    signal3 = signal1 && signal2;

    Serial.print("Signal1 : ");
    Serial.println(signal1);
    Serial.print("Signal2 : ");
    Serial.println(signal2);
    Serial.print("Signal3 : ");
    Serial.println(signal3);
    delay(800);
  }

  while(true){
    signal1 = digitalRead(inputPin1); // Read the state of the first input signal
    signal2 = digitalRead(inputPin2); // Read the state of the second input signal
    if(signal1_before != signal1){
        signal1_before = signal1;
        Serial.print("Signal1: ");
        Serial.println(signal1);
    } 
    if(signal2_before != signal2){
        signal2_before = signal2;
        Serial.print("Signal2: ");
        Serial.println(signal2);
    } 
  
    if (signal1 == HIGH && signal2 == HIGH) { // Check if both input signals are on
      signal3 = 1;
    } else {
      signal3 = 0;
    }
 
    if(signal3_before != signal3){
        signal3_before = signal3;
        Serial.print("Signal3: ");
        Serial.println(signal3);
    } 
  }
  //delay(100);
}

