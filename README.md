# Desiccator
Python project for logging weight from gram scales over time

README.TXT
ABOUT:
Desiccator is an app for recording change in weight over an extended period of time.
I made it to simplify moisture studies on donuts, but it can be used to record weight for any application.
The only restriction is the app is designed around the protocol the Ohaus Adventurer uses, so please 
make sure you only use this scale, or else the program will not work!

HOW TO USE:

First, extract Desiccator.zip to a folder of your liking

Set your scale to the right protocol
	Set scale to read in Grams by navigating to Item Settings>Weighing Units, and select Grams. Select Exit at the bottom of the touchscreen
	Navigate to Menu>Communication>RS232 Standard>Baud Rate and select 9600
	Select Back, the header at the top of the touchscreen will read RS232 Standard
	Select Transmission, then select 8N1
	Select Back, the header at the top of the touchscreen will read RS232 Standard
	Select Handshake, then select None at the bottom of the touchscreen
	Now select Exit at the bottom of the touchscreen to return to the home screen.
	Scale is now set to transmit over a USB cable
Set the auto-print interval on your scale
	Navigate to Menu>Communication>Print Settings>Auto Print>Interval (Seconds)
	Key in your desired frequency. The scale will output a reading every this-many seconds.
		For long recordings (>48 hours), this should be set to a minimum of 60 seconds to avoid huge file sizes.
Connect the scale to Desiccator
	Open Device Manager on your computer. You can search for it in the Start menu or do Windows+R, type "devmgmt.msc", and run.
	Navigate to Ports (COM & LPT), and open the drop-down menu.
	Take note of which COM numbers are already in use. eg. COM1, COM2, COM3... These appear at the end of each device's name.
	Plug the scale into a USB port on your computer.
	Device manager will refresh. Take note of the new COM number. This is the port assigned to your scale.
	Open Desiccator.exe, click Refresh Ports, and select the port assigned to your scale.
		Note: "Test Port" function should only be used when you are auto-printing in very short intervals (<5 seconds)
	Your scale is now connected to Desiccator!
Start recording
	With the scale connected, click Select CSV File in Desiccator. Create a file with your desired name where you would like to save the weight log.
	Click Start Logging!
	You should now see a timestamped recording at the bottom of the screen. You should also see a new .csv file in the location you previoulsy specified.
	
When you're done, click Stop Logging to safely stop the logging process.

This is open source software so feel free to modify, copy, iterate, etc.. 
Source python code can be found in the /source directory of the zip
-Ethan H 
