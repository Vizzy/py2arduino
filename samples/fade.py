'''
 Fade
 
 This example shows how to fade an LED on pin 9
 using the analogWrite() function.
 
 This example code is in the public domain.
'''

def setup():
  global brightness, fadeAmount, led
  led = 13           # the pin that the LED is attached to
  brightness = 0    # how bright the LED is
  fadeAmount = 5    # how many points to fade the LED by
  # declare pin 9 to be an output:
  pinMode(led, OUTPUT)

def loop():
  global brightness, fadeAmount, led
  # set the brightness of pin 9:
  analogWrite(led, brightness)    

  # change the brightness for next time through the loop:
  brightness = brightness + fadeAmount

  # reverse the direction of the fading at the ends of the fade: 
  if brightness == 0 or brightness == 255:
    fadeAmount = -fadeAmount 

  # wait for 30 milliseconds to see the dimming effect    
  delay(30)