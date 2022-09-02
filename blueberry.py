from gpiozero import Button, LED, OutputDevice
from enum import IntEnum
from bluetoothaudio import BluetoothAudio, NoConnectedDeviceError
import subprocess
from datetime import datetime
from time import sleep

class Pins(IntEnum):

    LEFT_BUTTON_READ = 5
    MIDDLE_BUTTON_READ = 6
    RIGHT_BUTTON_READ = 13
    INDICATOR_LED = 11
    POWER_3V3_PIN = 0

# Initialize the buttons and LED
prev_button = Button(Pins.LEFT_BUTTON_READ, pull_up = True)
pauseplay_button = Button(Pins.MIDDLE_BUTTON_READ, pull_up = True)
next_button = Button(Pins.RIGHT_BUTTON_READ, pull_up = True)
indicator_led = LED(Pins.INDICATOR_LED)
power_pin = OutputDevice(Pins.POWER_3V3_PIN, active_high = True)

AUTOCONNECT_PAUSE = 5 # Delay in seconds between attempts of autoconnecting to a device
VERIFY_CONNECTION_PAUSE = 3 # Delay in seconds between verification that a device is connected
BUTTON_HOLD_TIME = 3 # Time in seconds to hold a button to activate its secondary use
WRITE_ERROR_LOG = False # Whether or not to write an error log when there is an exception

# Initialize Bluetooth Audio Object
bluetooth_audio = BluetoothAudio()

def shutdown():
    """ LED Blinks 5 times rapidly, music is paused, then Pi is shutdown.
    """
    indicator_led.blink(on_time=0.5, off_time=0.5, n=5, background=False)
    bluetooth_audio.pause()
    subprocess.call(['sudo', 'shutdown', 'now'])

def restart():
    """ LED Blinks 10 times extremely rapidly, music is paused, then Pi is shutdown and restart.
    """
    indicator_led.blink(on_time=0.25, off_time=0.25, n=10, background=False)
    bluetooth_audio.pause()
    subprocess.call(['sudo', 'shutdown', '-r', 'now'])

def run_if_connected(func):
    """ Takes a function and creates a new function that only runs when a bluetooth device is connected.
        The new function attempts to run and catches no connected device errors.
    """
    def new_func():
        if bluetooth_audio.connected_device:
            try:
                func()
            except NoConnectedDeviceError:
                # Even after the connected_device check, a no connected device error may occur
                # This happens when the connected_device was unexpectedly disconnected
                # In this case, verify_connection will update the connected_device to NullDevice
                bluetooth_audio.verify_connection()
                pass

    return new_func

def init_buttons():
    """ Initialize button functionality
    """
    power_pin.on()

    # Previous track, pause/play, and next track functionality on button presses
    prev_button.when_pressed = run_if_connected(bluetooth_audio.previous_song)
    pauseplay_button.when_pressed = run_if_connected(bluetooth_audio.play_pause_toggle)
    next_button.when_pressed = run_if_connected(bluetooth_audio.next_song)

    # Hold left button to shut off raspberry pi
    prev_button.hold_time = BUTTON_HOLD_TIME
    prev_button.when_held = shutdown

    # Hold middle button to pair to a new device
    pauseplay_button.hold_time = BUTTON_HOLD_TIME
    pauseplay_button.when_held = bluetooth_audio.autopair

    # Hold right button to automatically connect to a different paired device
    next_button.hold_time = BUTTON_HOLD_TIME
    next_button.when_held = bluetooth_audio.connect_different_device


if __name__ == '__main__':

    try:
        init_buttons()
        while True:
            # Attempt autoconnect till a device is connected
            # LED blinks slowly when attempting to connect
            indicator_led.blink(on_time=1, off_time=1, background=True)
            while not bluetooth_audio.autoconnect():
                sleep(AUTOCONNECT_PAUSE)
            # LED stays solid on when connection is established
            indicator_led.on()
            # Verify connection till connection is lost
            while bluetooth_audio.verify_connection():
                sleep(VERIFY_CONNECTION_PAUSE)

    except Exception as e:

        # If there is an error, blink led fast, log the error message and reboot the raspberry pi
        # This program is meant to start on bootup so the raspberry pi automatically acts as a bluetooth speaker
        # To make this program start automatically on bootup, add it to your /etc/rc.local

        if WRITE_ERROR_LOG:
            with open('errorlog.txt', 'a') as error_log:
                now = datetime.now()
                date_str = now.strftime("%m/%d/%Y")
                time_str = now.strftime("%H:%M:%S")

                error_log.write(f'Error on {date_str} @ {time_str}')
                error_log.write(f'Description: {str(e)}')
                error_log.write(f'Restarting')
        
        restart()




            

