# blueberry
Python scripts for using Raspberry Pi to add bluetooth audio to AUX speakers.
This project was made to add bluetooth audio to my 2008 Toyota Highlander, which has good built-in speakers and an AUX port, but no bluetooth connectivity.

blueberry.py is intended to be configured to run automatically at bootup using rc.local. 
It automatically connects to a bluetooth device and forwards incoming audio to the Raspberry Pi headphone jack, which can be plugged in to a speaker or car with an AUX cable. 

blueberry.py provides a physical 3 button interface:
| Action      | Button 1       | Button 2       | Button 3       |
| ----------- | -------------- | -------------- | -------------- |
| On Press    | Previous Track | Pause/Play     | Next Track     |
| On Hold     | Shutdown Pi    | Pair Device    | Connect Device |


If you would like to create your own interface, or do something different with bluetooth on the Raspberry Pi, bluetoothaudio.py and bluetoothctl.py contain useful functions for bluetooth audio and bluetooth connection with the Raspberry Pi.

### Requirements
Blueberry requires the bluetoothctl and bluealsa-aplay command line tools, which should already be installed on the latest versions of the Raspberry Pi OS.
Dbus and the dbus Python package are also required and should already be installed. 
The gpiozero Python package is required for button input via GPIO pins, and is preinstalled on Raspberry Pi OS.
The pexpect Python package is the only additional requirement you may need to install.
