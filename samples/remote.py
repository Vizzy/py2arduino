remote_switch = 8 # switch1 pin
IR_switch = 9 # switch2
light_switch = 10  # switch3

buttonLeft = 3
buttonForward = 5
buttonRight = 6
buttonBack = 4

def setup():
  # BT MASTER setup code
  Serial.begin(115200)
  Serial.print("$$$")
  delay(100)
  Serial.println("SM,1")
  delay(100)
  Serial.println("C,0006664EE472")  # the specific MAC address for the bt module
  delay(100)
  Serial.println("---")
  
  # pin setup code
  pinMode(13, OUTPUT) # LED on pin 13
  pinMode(remote_switch, INPUT_PULLUP) # monitor pin state, enable pullups to make pin high
  pinMode(IR_switch, INPUT_PULLUP) # monitor pin state, enable pullups to make pin high
  pinMode(light_switch, INPUT_PULLUP) # monitor pin state, enable pullups to make pin high


def loop():
    
    if (checkPressed(remote_switch)):

      Serial.println("0")
      if (checkPressed(buttonLeft)):
          Serial.println('l')
        
      if (checkPressed(buttonForward)):
          Serial.println('f')
       
      if (checkPressed(buttonRight)):
          Serial.println('r')   
         
      if (checkPressed(buttonBack)):
          Serial.println('b') 

    elif checkPressed(IR_switch):
      Serial.println("1")

    elif checkPressed(light_switch):
      Serial.println("2")

    delay(300)  # delay for debounce

def checkPressed (button: int) -> bool:
  buttonState = digitalRead(button)
  
  if buttonState == LOW:
    return True

  else:
    return False

