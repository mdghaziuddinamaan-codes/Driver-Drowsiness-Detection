#include <LiquidCrystal.h>

// 16x2 parallel LCD: RS, E, D4, D5, D6, D7
LiquidCrystal lcd(2, 3, 4, 5, 6, 7);

const int buzzerPin = 8;
const int ledPin = 13;

// Python sends 'a' when drowsy/sleeping and 'b' when active.
char driverStatus = 'b';

void showActiveMessage() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Drive Safe");
  lcd.setCursor(0, 1);
  lcd.print("Eyes Open");
}

void showDrowsyMessage() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Please Wake Up");
  lcd.setCursor(0, 1);
  lcd.print("Drowsiness!");
}

void setup() {
  Serial.begin(9600);

  pinMode(buzzerPin, OUTPUT);
  pinMode(ledPin, OUTPUT);
  digitalWrite(buzzerPin, LOW);
  digitalWrite(ledPin, LOW);

  lcd.begin(16, 2);
  lcd.setCursor(0, 0);
  lcd.print("Driver Sleep");
  lcd.setCursor(0, 1);
  lcd.print("Detection System");
  delay(1800);

  showActiveMessage();
}

void loop() {
  while (Serial.available() > 0) {
    char incoming = Serial.read();

    if (incoming == 'a' && driverStatus != 'a') {
      driverStatus = 'a';
      showDrowsyMessage();
      digitalWrite(buzzerPin, HIGH);
      digitalWrite(ledPin, HIGH);
    }
    else if (incoming == 'b' && driverStatus != 'b') {
      driverStatus = 'b';
      showActiveMessage();
      digitalWrite(buzzerPin, LOW);
      digitalWrite(ledPin, LOW);
    }
  }
}
