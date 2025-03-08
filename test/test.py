import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library
import time

GPIO.setwarnings(False) # Ignore warning for now
GPIO.setmode(GPIO.BOARD) # Use physical pin numbering
GPIO.setup(18, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # Set pin 10 to be an input pin and set initial value to be pulled down

start_time = None

try:
    while True: # Run forever
        if GPIO.input(18) == GPIO.HIGH:
            start_time = time.time()
            print("high")
        else:
            print("low")
            end_time = time.time()
            try:
                duration = (end_time - start_time) * 1000
                print(f"Button was pressed for {duration:.2f} milliseconds")
            except:
                pass
            
        time.sleep(0.05) # Add a small delay to debounce

except KeyboardInterrupt:
    pass

finally:
    GPIO.cleanup()
