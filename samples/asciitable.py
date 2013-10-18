def setup():
    Serial.begin(9600)

    # while not Serial:
    #     pass
    #     # wait for serial port to connect. Needed for Leonardo only

    # prints title with ending line break 
    Serial.println("ASCII Table ~ Character Map")

def loop(): 
    thisByte = 33

    Serial.write(thisByte)
    Serial.print(", dec: ")
    Serial.print(thisByte)
    Serial.print(", hex: ")
    # prints value as string in hexadecimal (base 16):
    Serial.print(thisByte, HEX)

    Serial.print(", oct: "); 
    # prints value as string in octal (base 8);
    Serial.print(thisByte, OCT)     

    Serial.print(", bin: ") 
    # prints value as string in binary (base 2) 
    # also prints ending line break:
    Serial.println(thisByte, BIN)   

    # if printed last visible character '~' or 126, stop: 
    if thisByte == 126:     # you could also use if (thisByte == '~') {
      # This loop loops forever and does nothing
      while True: 
        continue 

    # go on to the next character
    thisByte += 1 