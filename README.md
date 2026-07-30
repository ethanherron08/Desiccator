ABOUT:
Desiccator is an app for recording change in weight over an extended period of time.
I made it to simplify moisture studies on donuts, but it can be used to record weight for any application.
The only restriction is the app is designed around the protocol the Ohaus Adventurer uses, so please 
make sure you only use this scale, or else the program will not work!

HOW TO USE:
Open Desiccator.exe
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
	Without the scale connected to your computer, click the Refresh button, followed by the "port" drop down and take note of the available ports.
	Connect the scale via USB
	Click refresh again, click the drop down once more, and select the port that was not available before connecting.
	Click "Test Port"
	If that was successful, your scale is now connected to Desiccator!
Start recording
	If you seelcted the correct protocol in the first section of the directions, there should be no need to tamper with the default serial settings.
	With the scale connected, click Select CSV File in Desiccator. Create a file with your desired name where you would like to save the weight log.
	Click Start Logging!
	You should now see a timestamped recording at the bottom of the screen. You should also see a new .csv file in the location you previoulsy specified.
	
When you're done, click Stop Logging to safely stop the logging process.

This is open source software so feel free to modify, copy, iterate, etc.. 
-Ethan H 
