# -*- coding: utf-8 -*-
"""
Created on Wed Jun 19 15:21:28 2024

@author: Felix Wechsler (roflmaostc), Gordon Su (dataricerunner)

MIT License

Copyright (c) 2024 Felix Wechsler (roflmaostc) <fxw+git@mailbox.org>, Gordon Su (dataricerunner)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

WELCOME = "\
 /$$      /$$           /$$                                             \n\
| $$  /$ | $$          | $$                                             \n\
| $$ /$$$| $$  /$$$$$$ | $$  /$$$$$$$  /$$$$$$  /$$$$$$/$$$$   /$$$$$$  \n\
| $$/$$ $$ $$ /$$__  $$| $$ /$$_____/ /$$__  $$| $$_  $$_  $$ /$$__  $$ \n\
| $$$$_  $$$$| $$$$$$$$| $$| $$      | $$  \ $$| $$ \ $$ \ $$| $$$$$$$$ \n\
| $$$/ \  $$$| $$_____/| $$| $$      | $$  | $$| $$ | $$ | $$| $$_____/ \n\
| $$/   \  $$|  $$$$$$$| $$|  $$$$$$$|  $$$$$$/| $$ | $$ | $$|  $$$$$$$ \n\
|__/     \__/ \_______/|__/ \_______/ \______/ |__/ |__/ |__/ \_______/ \n\
                                                                        \n\
   /$$                     /$$        /$$$$$$  /$$$$$$$  /$$$$$$$       \n\
  | $$                    | $$       /$$__  $$| $$__  $$| $$__  $$      \n\
 /$$$$$$    /$$$$$$       | $$      | $$  \ $$| $$  \ $$| $$  \ $$      \n\
|_  $$_/   /$$__  $$      | $$      | $$$$$$$$| $$$$$$$/| $$  | $$      \n\
  | $$    | $$  \ $$      | $$      | $$__  $$| $$____/ | $$  | $$      \n\
  | $$ /$$| $$  | $$      | $$      | $$  | $$| $$      | $$  | $$      \n\
  |  $$$$/|  $$$$$$/      | $$$$$$$$| $$  | $$| $$      | $$$$$$$/      \n\
   \___/   \______/       |________/|__/  |__/|__/      |_______/       \n\
"



from zaber_motion.ascii import Connection
from zaber_motion import Units
from zaber_motion.ascii import WarningFlags

from ALP4 import *

import datetime
import time
import tqdm
import os
import argparse
import numpy as np
import warnings
from PIL import Image
from colorama import Fore
import cv2
# to enable .exr image loading https://github.com/opencv/opencv/issues/21928
os.environ["OPENCV_IO_ENABLE_OPENEXR"]="1"

# this assumes our DMD model and grayscale, otherwise this number might change
MAX_FREQUENCY_DMD_GRAYSCALE_8BIT = 290


def process_arguments():
  
    """
   Parse and process command-line arguments.

   Returns:
       argparse.Namespace: Parsed command-line arguments.
   """
    
    # Instantiate the parser
    parser = argparse.ArgumentParser(description='Optional app description')
    
    parser.add_argument('-v', '--velocity', help="rotation speed in deg/sec, default is 60.0",
                        action="store", type=float, default=40.0)
     
    parser.add_argument('-n', '--num_turns', help="number of turns, default is 3",
                        action="store", type=int, default=3)
    
    parser.add_argument('-d', '--duty_cycle', help="duty cycle. This is a factor which reduces the global intensity of all images. This can be used to fine tune the intensity. The duty cycle has a lower limit how little the intensity can be. This depends on the image rate of the DMD.",
                        action="store", type=float, default=1.0)               
                        
    parser.add_argument('-p', '--path', help="path to images, no default. This can be either a folder containing images (such as .png or .erf). But also a path to a compressed numpy file (.npz) is possible. Compressed numpy expects a 3D array of shape (ANGLES X WIDTH X HEIGHT).",
                        action="store")
    
    parser.add_argument('-ps', '--port_stage', help="port of the stage, default is \"COM4\"",
                        action="store", type=str, default="COM6")
    
    parser.add_argument('-a', '--amplitude', help="Amplitude of the sinusoidal wobble in DMD pixel, default 0.", 
                        action = "store", type=float, default = 0)

    parser.add_argument('-ph', '--phase', help="Phase shift of the sinusoidal wobble in degrees, default 0.",
                        action = "store", type=float, default = 0)
    
    parser.add_argument('--reverse_angles', action='store_true', help="Reverse the angle, equivalent to rotating reverse direction",
                        default=False)

    parser.add_argument('--flip_vertical', action='store_true', help="Flip vertical direction of DMD images.",
                        default=False)
                        
    parser.add_argument('--flip_horizontal', action='store_true', help="Flip horizontal direction of DMD images.",
                        default=False)

    parser.add_argument('--shift_vertical', help="Move patterns by a certain amount of DMD pixels vertically.",
                        action = "store", type=int, default = 0)

    parser.add_argument('--mode_horizontal', action='store_true', help="This indicates the long edge of the DMD is in the rotation plane. Wobbling correction is applied in the different axis than without this flag.",
                        default=False)

    parser.add_argument('-f', "--flat_field", action = 'store', help = "Flat field correction image for DMD. DMD is divided by this", type=str, default = "None")
                        
    parser.add_argument('--notes', action = 'store', help = "Write additional notes to printing log", type=str, default = "None")
 
    printing_parameters = parser.parse_args()
    
       
    # just some sanity checks
    assert 0 < printing_parameters.duty_cycle <= 1.0, "Duty cycle has to be > 0 and smaller equal than 1"
    assert 0 < printing_parameters.velocity <= 120, "Do not turn the stage too fast or too slow"
    assert printing_parameters.num_turns >= 1, "Do more than 0 rotations, only integer amount supported"
        
    print("All printing parameters processed succesfully.\n")
    return printing_parameters

# this function is called to store the log file
def write_parameters(printing_parameters):
    with open('printing_log.txt', 'a') as file1:
        file1.write("\n" + str(datetime.datetime.now()))
        iterable = vars(printing_parameters).items()
        for parameter in iterable:
            file1.write(" " + str(parameter))


    
def open_exr(filepath):
    return cv2.imread(filepath,  cv2.IMREAD_ANYCOLOR | cv2.IMREAD_ANYDEPTH)  
        
def load_images_and_correct_rotation_axis_wobbling(printing_parameters):

    """
    Shape images and apply wobbling/ordering/flip corrections
    
    Returns:
        numpy array: 2D array where the first dimension is images
    """
    
    print("Start loading images into RAM.")
    
    if printing_parameters.path.endswith(".npz"):
        print("Loading patterns from compressed .npz file.")
        images = np.load(printing_parameters.path)["patterns"]
    else:
        filelist = os.listdir(printing_parameters.path)
        filelist = sorted(filelist)
        print("Loading patterns from folder of images")
        images = []
        for i in tqdm.tqdm(filelist):
            image = os.path.join(printing_parameters.path, i)
            if os.path.splitext(image)[-1] == ".exr":
                images.append(open_exr(image))
            else:
                images.append(np.asarray(Image.open(image).convert('L')))

        print("The detected image shape is {}".format(images[0].shape))
        
        images = np.array(images)
    
    if images.shape[1] == 1024 and images.shape[2] == 768:
        print("It was detected that the images have shape 1024x768. Let's do the transpose to have alignment on DMD correctly")
        images = np.swapaxes(images, 2, 1)
    
    if printing_parameters.reverse_angles:
        print("Reverse angular order images")
        # from [0,1,2,3] to [0,3,2,1]
        # but we preserve that the first image is still the 0° pattern.
        # matters for certain geometries (such as square!)
        images = np.roll(images[::-1, :, :], 1, axis=0)

    if printing_parameters.flip_vertical:
        print("Flip vertical axis of images.")
        if printing_parameters.mode_horizontal:
            images = images[:, ::-1, :]
        else: 
            images = images[:, :, ::-1]  
        

    if printing_parameters.flip_horizontal:
        print("Flip horizontal axis of images.")
        if printing_parameters.mode_horizontal:
            images = images[:, :, ::-1]
        else: 
            images = images[:, ::-1, :]

    # shift patterns by a DMD pixel amount for better vertical alignment
    # sign corresponds to camera sign
    if printing_parameters.shift_vertical != 0:
        print("Shift patterns verticall by {}".format(printing_parameters.shift_vertical))
        images = np.roll(images, -printing_parameters.shift_vertical, axis=2)

    assert (images.shape[1] == 768 and images.shape[2] == 1024), "Image size is not 768 x 1024"
    
    
    
    if printing_parameters.amplitude == 0 and printing_parameters.phase == 0:
        print()
        images = np.array(images / np.max(images) * 255, dtype=np.uint8)
        return images.reshape(images.shape[0], -1)
    
    # endpoint=False is important! Otherwise 0° and 360° (which is the same) are both included
    angles = np.linspace(0, 2 * np.pi, images.shape[0], endpoint=False)
    
    # wobbling correction is done by integer shifts of the image
    print("\nApply wobbling correction:")
    for i in tqdm.tqdm(range(images.shape[0])):
        φ = angles[i]
        shift_value = round(printing_parameters.amplitude * np.sin(φ + 
                                                                 printing_parameters.phase / 360 * 2 * np.pi))

        if printing_parameters.mode_horizontal:
            axis = 1
        else:   
            axis = 0
        
        images[i, :, :] = np.roll(images[i, :, :], int(np.round(shift_value)), axis=axis)
    
    print()



    
    if printing_parameters.flat_field != "None":
        print("Applying flat field correction")
        # reshaping batch dimension first
        flat_field = np.load(printing_parameters.flat_field)[None, :, ::-1]
        flat_field /= np.max(flat_field)
        print(flat_field.shape)
        print(images.shape)
        print(np.max(flat_field))
        print(np.min(flat_field))
        images = images / flat_field
        print(np.max(images))
        images = np.array(images / np.max(images) * 255, dtype=np.uint8)
        print(np.max(images))


    # flatten images for DMD
    images = np.array(images / np.max(images) * 255, dtype=np.uint8)
    return images.reshape(images.shape[0], -1)


def initialize_DMD(images, printing_parameters):
    
    """
    Initialize the DMD.

    Returns:
        tuple: The DMD object and number of images.
    """

    # Load the Vialux .dll
    dmd = ALP4(version = '4.2')
    # Initialize the device
    dmd.Initialize()

    print("Temperature checks:")
    for T, B in zip([ALP_DDC_FPGA_TEMPERATURE, ALP_APPS_FPGA_TEMPERATURE, ALP_PCB_TEMPERATURE],
                    ["DDC FPGAs Temperature Diode", "Application FPGAs Temperature Diode", "Board temperature"]):
        print("\tTemperature of {} is: {:.1f}°C".format(B, dmd.DevInquire(T) / 256))


    # allocate a sequence on the DMD
    dmd.SeqAlloc(nbImg = images.shape[0], bitDepth = 8)
    # Send the image sequence as a 1D list/array/numpy array
    print("We are loading {} images onto the DMD.".format(len(images)))
    dmd.SeqPut(imgData = images)
    # how many images per seconds are required
    frequency_image = printing_parameters.velocity / 360 * images.shape[0]
    # this is the timings we try to set on the DMD, we subtract some small deltas to be sure that trigger listens. This delta is required
    # check the manual. The manual of the DMD says at least ~80µs. Just be sure with 200µs
    pictureTime = ((1 / frequency_image) - 200e-6)
    # DMD requires that there is a small delta between pictureTime and illuminationTime. Same again here
    illuminationTime = (pictureTime - 200e-6) * printing_parameters.duty_cycle
    
    # hardware specific parameter, minimum illumation time in µs
    min_illumination_time = dmd.SeqInquire(ALP_MIN_ILLUMINATE_TIME)
    assert (frequency_image < MAX_FREQUENCY_DMD_GRAYSCALE_8BIT), ("DMD can only do {}Hz with 8Bit grayscale. Choose a lower velocity, you tried to do {:.1f}Hz".format(MAX_FREQUENCY_DMD_GRAYSCALE_8BIT, frequency_image))
    
    # in µs
    pictureTimeDMD = round(pictureTime * 1_000_000)
    # in µs
    illuminationTimeDMD = round(illuminationTime * 1_000_000)
    assert illuminationTimeDMD > min_illumination_time, \
        "You tried to set an illuminationTime {:.0f}µs which is lower than the hardware limit {:.0f}µs. Try to increase duty_cycle".format(illuminationTimeDMD, min_illumination_time)
    
    print("illuminationTime on DMD is {:.0f}µs".format(illuminationTimeDMD))
    # important call. pictureTime is the total time of each picture. illuminationTime is how long the image is on. Almost the same
    # just a small delta difference -> see manual
    dmd.SetTiming(pictureTime = pictureTimeDMD, illuminationTime=illuminationTimeDMD)
    # set stage to be slave
    dmd.ProjControl(ALP_PROJ_MODE, ALP_SLAVE)
    # DMD should listen to a rising edge of the trigger
    dmd.DevControl(ALP_TRIGGER_EDGE, ALP_EDGE_RISING)
    print("Done setting up DMD and images are loaded.\n")
    return dmd, images.shape[0], illuminationTimeDMD


def initialize_stage(printing_parameters, triggers_per_round):
   
    """
   Initialize the stage and set up triggers. There are two triggers. One just is on, once the stage did one full round of turning.
   The second triggers always toggles at a frequency which is the frequency we want to display the images.
   Those two output triggers go to an Arduino which does the logical AND of those two. 
   Then the triggers goes into the DMD

   Args:
       printing_parameters (argparse.fstage Namespace): Parsed command-line arguments.
       triggers_per_round (int): Number of triggers per round.

   Returns:
       axis: The axis object of the stage.
   """
   
    
   
    print("Initialize stage, set triggers and initialize triggers.\n")

    stage_handler = Connection.open_serial_port(printing_parameters.port_stage)
    
    # the number of steps for one 360° rotation
    STAGE_ONE_TURN_STEPS = int(stage_handler.generic_command("get limit.cycle.dist").data)
    
    # assert check. Since the stage can fire the trigger only at certain integer steps, we need to be sure by that.
    assert ((STAGE_ONE_TURN_STEPS % (2 * triggers_per_round)) == 0), "{} has to be divisible by 2 * {}. The first number is the integer steps of the stage. The second number is the number of images.".format(STAGE_ONE_TURN_STEPS, triggers_per_round)
    
        
    # indicates the steps to turn one round on the stage")
    #Trigger 1 - Set digital output 1 == 1 when pos > 360°
    stage_handler.generic_command("system restore")
    stage_handler.generic_command("trigger 1 when 1 pos >= {}".format(STAGE_ONE_TURN_STEPS))
    stage_handler.generic_command('trigger 1 action a io set do 1 1')
    stage_handler.generic_command("trigger 1 enable")
    
    # when it is below <360°, set trigger hard to 0
    stage_handler.generic_command("trigger 3 when 1 pos < {}".format(STAGE_ONE_TURN_STEPS))
    stage_handler.generic_command('trigger 3 action a io set do 1 0') 
    stage_handler.generic_command("trigger 3 enable")
    
    #Trigger 2 - toggle digital output 2 based on distance interval
    stage_handler.generic_command("trigger 2 when 1 dist {}".format(STAGE_ONE_TURN_STEPS // (2 * triggers_per_round)))
    stage_handler.generic_command("trigger 2 action a io set do 2 t")
    stage_handler.generic_command("trigger 2 enable")
    
    # set in the beginning hard to 1
    stage_handler.generic_command("trigger 4 when 1 pos == 0")
    stage_handler.generic_command("trigger 4 action a io set do 2 1")
    stage_handler.generic_command("trigger 4 enable")
    
    # find the correct axis
    device_list = stage_handler.detect_devices()
    device = device_list[0]
    axis = device.get_axis(1)
    axis.home()
    
    # check temperature
    warning_flags = axis.warnings.get_flags()
    if WarningFlags.CONTROLLER_TEMPERATURE_HIGH in warning_flags:
        print("Device is overheating!")
    else:
        temperature = stage_handler.generic_command("get driver.temperature").data
        print("The current temperature of the stage is {} °C\nIt is recommended that the temperature is below 80 °C\n".format(temperature))
        
  
    
    return axis, STAGE_ONE_TURN_STEPS
    

def print_TVAM(axis, dmd, printing_parameters, STAGE_ONE_TURN_STEPS):
    
    """
   Print using the TVAM process.

   Args:
       axis: The axis object of the stage.
       dmd: The DMD object.
       printing_parameters (argparse.Namespace): Parsed command-line arguments.
   """
    #axis.move_velocity(printing_parameters.velocity, unit=Units.ANGULAR_VELOCITY_DEGREES_PER_SECOND)
    # turn DMD on, now it will listen to triggers
    dmd.Run()

    # move stage to an absolute position, this command is non-block, so it moves to the next python line
    axis.move_absolute(STAGE_ONE_TURN_STEPS * (printing_parameters.num_turns + 1) - 1, Units.NATIVE, 
                       False, 
                       printing_parameters.velocity, Units.ANGULAR_VELOCITY_DEGREES_PER_SECOND)
       
    # let the bar monitor the print. Effectively this code is just for inspection, the stage turns and sends triggers which the DMD listens  to
    # so everything is synchronized by the stage and not this code.
    try:
        # warm up round
        position = axis.get_position(unit=Units.NATIVE)
        with tqdm.tqdm(total = 360, desc = "Acceleratinggggg, print after 360°", bar_format= '{l_bar}{bar}{r_bar}') as pbar:
            while position < STAGE_ONE_TURN_STEPS:
                position = axis.get_position(unit=Units.NATIVE)
                if position < STAGE_ONE_TURN_STEPS:
                    pbar.update(int(position / STAGE_ONE_TURN_STEPS * 360) - pbar.n)
        
        
        # now the print is really on
        with tqdm.tqdm(total = 360 * printing_parameters.num_turns, desc = "Printinggggg", bar_format= '{l_bar}{bar}{r_bar}') as pbar:
            while position < STAGE_ONE_TURN_STEPS * (1 + printing_parameters.num_turns) - 1:
                position = axis.get_position(unit=Units.NATIVE)
                pbar.update(int(position / STAGE_ONE_TURN_STEPS * 360) - pbar.n - 360)
                
        stop_dmd_stage(axis, dmd)
    # just some interrupt handling
    except KeyboardInterrupt:
        print("Keyboard interrupt. Homing stage and stop.")
        stop_dmd_stage(axis, dmd)
    print("\nPrint over, inspect sample")
    printing_time = 360 / printing_parameters.velocity * printing_parameters.num_turns
    print("Total printing time {:.1f}s with duty cycle of {}.\n".format(printing_time, printing_parameters.duty_cycle))
    return


def stop_dmd_stage(axis, dmd):
   
    """
   Stop the DMD and stage.

   Args:
       axis: The axis object of the stage.
       dmd: The DMD object.
   """
    
    try:
        dmd.Halt()
        # Free the sequence from the onboard memory
        dmd.FreeSeq()
        # De-allocate the device
        dmd.Free()
    except:
        pass

    axis.stop()
    axis.home()
    return
    
def write_result(illuminationTime):
    result = input("Please add your results ")
    with open('printing_log.txt', 'a') as file1:
        file1.write(" IlluminationTime:" + " " + str(illuminationTime) + "µs")
        try:
            file1.write(" Final results:" + " " + result)
        except:
            print("Please enclose your result in \" \"")
            write_result()


# put pieces together
def main():
    #print(WELCOME)
    print("")
    print("-------------------- 1/5 -------------------------------------")
    printing_parameters = process_arguments()
    write_parameters(printing_parameters)
    print("-------------------- 2/5 -------------------------------------")
    images = load_images_and_correct_rotation_axis_wobbling(printing_parameters)
    print("-------------------- 3/5 -------------------------------------")
    dmd, num_of_images, illuminationTime = initialize_DMD(images, printing_parameters)
    print("-------------------- 4/5 -------------------------------------")
    axis_stage, STAGE_ONE_TURN_STEPS = initialize_stage(printing_parameters, triggers_per_round=num_of_images)
    print("-------------------- 5/5 -------------------------------------")
    print_TVAM(axis_stage, dmd, printing_parameters, STAGE_ONE_TURN_STEPS)
    write_result(illuminationTime)
    
    
    
if __name__ == "__main__":
    main()

    
