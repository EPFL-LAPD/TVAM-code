# README for Control software of TVAM printer

## Installation
Install drivers for ALP DMD first.
Get a Python version and run:
```python
pip install numpy opencv-python pillow tqdm ALP4lib
```


## Full help
```
-h, --help            					show this help message and exit
-p PATH_OR_NPZ_FILE, --path PATH_OR_NPZ_FILE            path to images, no default. This can be either a folder containing images (such as .png or
                                                        .erf). But also a path to a compressed numpy file (.npz) is possible. Compressed numpy expects
                                                        a 3D array of shape (ANGLES X WIDTH X HEIGHT).
-v VELOCITY, 		--velocity VELOCITY  		rotation speed in deg/sec, default is 60.0
-n NUM_TURNS, 		--num_turns NUM_TURNS 		number of turns, default is 3
-d DUTY_CYCLE, 		--duty_cycle DUTY_CYCLE 	This is a factor which reduces the global intensity of all images. This can be used to fine tune the intensity.
							The duty cycle has a lower limit how little the intensity can be. This depends on the image rate of the DMD
-ps PORT_STAGE, 	--port_stage PORT_STAGE 	port of the stage, default is "COM6"
-a AMPLITUDE, 		--amplitude AMPLITUDE 		Amplitude of the sinusoidal wobble in DMD pixel,default 0.
-ph PHASE, 		--phase PHASE 			Phase shift of the sinusoidal wobble in degrees, default 0.
--reverse_angles  					Reverse the angle, equivalent to rotating reverse direction
--flip_vertical       				        Flip vertical direction of DMD images.
--flip_horizontal					Flip horizontal direction of DMD images.		
--notes NOTES    					Write additional notes to printing log  
```

# Hardware
The stage gives two output triggers (see `initialize_stage`). 
One trigger is activated after one round, the second toggles in the speed of how many images we need per rotation.
The Arduino takes both inputs and does a digital read (microseconds delay, so quite fast). 
And the Arduino does the logical AND of both inputs and provides another output.
This is fed to the input of the DMD.
So the Arduino code is [here](arduino_io_board_code/arduino_io_board_code.ino). 
The python code to run the stage and prepare the DMD is [tvam_code.py](tvam_code.py).
The lasers are not triggered, they are just always on. But since the DMD is off by default, no light goes through the printing arm.


# DMD
We are using [this library](https://github.com/wavefrontshaping/ALP4lib). Check regularly for updates. 


# Simply checks
To check that everything is functional, you can call:
* ` python .\tvam_code.py -p .\images_10\ -n 15 -ph 78 -a 11 -v 50 --flip_vertical`
* Check with the camera from behind (USB one) to see if the 10 numbers appear regularly. When the illumination stops, it should stop at 9!
* If it doesn't look regular or does not stop at the 9, something is broken

## Zaber
### Stage
We use the Zaber X-RSW60C stage.

One of them has the modified I/O output which allows the stage to act as a master.
In this script, Zaber X-RSW60C stage is programmed to send 2 electrical triggers
(one that will turn on after the stage has done a full rotation and another that
fire once every given interval to signal to the DMD to change its image projection)



# Usage (old lab PC)
* Start **Anaconda Powershell Prompt**
* Use the base Python environment
* `cd .\Documents\TVAM-code\`
* Call `python .\tvam_code.py --help` to see the help
* A typical call is: `python .\tvam_code.py -p D:\PrintingPython\Printing_GelMA\ComplexAcinus\Patterns60deg_tilted_up\  -n 8 -ph 70 -a 12 -v 40 --flip_vertical -d 0.8`
* The script logs all calls into `printing_log` such that all prints with all parameters and additional notes are saved with timestamps

# Usage (new lab PC, since 2.10.2024)
* Start **Anaconda Powershell Prompt**
* Use the base Python environment
* `cd .\TVAM-code\`
* Call `python .\tvam_code.py --help` to see the help
* A typical call is: `python .\tvam_code.py -p D:\PrintingPython\Printing_GelMA\ComplexAcinus\Patterns60deg_tilted_up\  -n 8 -ph 70 -a 12 -v 40 --flip_vertical -d 0.8`
* The script logs all calls into `printing_log` such that all prints with all parameters and additional notes are saved with timestamps

# Usage with Mitsuba
* Mitsuba has the patterns flipped upside down. So use `--flip_vertical` and you should be good to go. The turning convention should already match (after the transpose we do in the code already. Mitsuba exports height and width of the images flipped compared to our code).
* To check the rotation direction convention, use the square vials. In those patterns the rotation direction is intuitive to understand.


# Steps to prepare good printing condition
* Turn Laser Sign on
* Turn lasers diodes on (top two). Put them in manual mode and increase current to 2x500mA each.
* Turn ALP software on. Initialize DMD. Put white test pattern. Check with the camera from behind that DMD is illuminated homogenously. Otherwise adjust fibre outcoupling lens.
* Check wobble. For that insert the metal tip and observe with the camera from behind. Run `python tvam_code.py -D images_line\ -n 10 -a 11 -ph 77`. Adapt values of amplitude and phase of the script such that the tip follows the center line. Also adapt the center position with the micrometer screw in the setup.
* Now you are ready to go. Just give it a test run with your patterns and check if everything looks good.
* If your printing results are weird. Try `--flip_horizontal` OR `--reverse_angles`. The rotation direction in TVAM makes a difference so maybe your turning convention of the patterns is just the wrong one. There is two choices. Best way to find out, is just to look at the printed results. If the sample is asymmetric, it will make a difference!



