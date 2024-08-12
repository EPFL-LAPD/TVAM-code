# -*- coding: utf-8 -*-
"""
Created on Wed Jun 19 15:21:28 2024

@author: adminlapd
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
   /$$                                                                  \n\
  | $$                                                                  \n\
 /$$$$$$    /$$$$$$                                                     \n\
|_  $$_/   /$$__  $$                                                    \n\
  | $$    | $$  \ $$                                                    \n\
  | $$ /$$| $$  | $$                                                    \n\
  |  $$$$/|  $$$$$$/                                                    \n\
   \___/   \______/                                                     \n\
                                                                        \n\
 /$$        /$$$$$$  /$$$$$$$  /$$$$$$$                                 \n\
| $$       /$$__  $$| $$__  $$| $$__  $$                                \n\
| $$      | $$  \ $$| $$  \ $$| $$  \ $$                                \n\
| $$      | $$$$$$$$| $$$$$$$/| $$  | $$                                \n\
| $$      | $$__  $$| $$____/ | $$  | $$                                \n\
| $$      | $$  | $$| $$      | $$  | $$                                \n\
| $$$$$$$$| $$  | $$| $$      | $$$$$$$/                                \n\
|________/|__/  |__/|__/      |_______/                                 \n\
"





from zaber_motion.ascii import Connection
from zaber_motion import Units
import time
from zaber_motion.ascii import WarningFlags
from tqdm import tqdm
from ALP4 import *


import os
import argparse
import numpy as np
from multiprocessing import Pool

import tqdm
from PIL import Image
import os


STAGE_ONE_TURN_STEPS = 384_000



def process_arguments():
  
    """
   Parse and process command-line arguments.

   Returns:
       argparse.Namespace: Parsed command-line arguments.
   """
    
    # Instantiate the parser
    parser = argparse.ArgumentParser(description='Optional app description')
    
    parser.add_argument('-v', '--velocity', help="rotation speed in deg/sec, default is 60.0",
                        action="store", type=float, default=60.0)
     
    parser.add_argument('-n', '--num_turns', help="number of turns, default is 3",
                        action="store", type=int, default=3)
    
    parser.add_argument('-p', '--path', help="path to images, no default",
                        action="store")
    
    parser.add_argument('-ps', '--port_stage', help="port of the stage, default is \"COM4\"",
                        action="store", type=str, default="COM4")
    
    parser.add_argument('-a', '--amplitude', help="Amplitude of the sinusoidal wobble in DMD pixel, default 0.", 
                        action = "store", type=float, default = 0)

    parser.add_argument('-ph', '--phase', help="Phase shift of the sinusoidal wobble in degrees, default 0.",
                        action = "store", type=float, default = 0)
    
    parser.add_argument('--reverse_angles', action='store_true', help="Reverse the angle, equivalent to rotating reverse direction",
                        default=False)

    parser.add_argument('--flip_vertical', action='store_true', help="Flip vertical direction of DMD images.",
                        default=False)
 
    args = parser.parse_args()
    assert 0 < args.velocity <= 120, "Do not turn the stage too fast or too slow"
    assert args.num_turns >= 1, "Do more than 0 rotations, only integer amount supported"
    return args

    

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


def initialize_stage(printing_parameters, triggers_per_round=1000):
   
    """
   Initialize the stage and set up triggers.

   Args:
       printing_parameters (argparse.fstage Namespace): Parsed command-line arguments.
       triggers_per_round (int): Number of triggers per round, default is 1000.

   Returns:
       axis: The axis object of the stage.
   """
   
    print("Initialize stage, initialize triggers and reset triggers to 0\n")

    assert ((STAGE_ONE_TURN_STEPS % (2 * triggers_per_round)) == 0), "{} has to be divisible by 2 * {}".format(STAGE_ONE_TURN_STEPS, triggers_per_round)

    stage_handler = Connection.open_serial_port(printing_parameters.port_stage)
    
        

    # indicates the steps to turn one round on the stage")

    #Trigger 1 - Set digital output 1 == 1 when pos > 360°
    stage_handler.generic_command("system restore")
    # trigger when position >= 360°
    stage_handler.generic_command("trigger 1 when 1 pos >= {}".format(STAGE_ONE_TURN_STEPS))
    #set digital output 1 to 1
    stage_handler.generic_command('trigger 1 action a io set do 1 1')
    stage_handler.generic_command("trigger 1 enable")
    
    
    stage_handler.generic_command("trigger 3 when 1 pos < {}".format(STAGE_ONE_TURN_STEPS))
    # when it is below <360°, set trigger hard to 0
    stage_handler.generic_command('trigger 3 action a io set do 1 0') 
    stage_handler.generic_command("trigger 3 enable")
    
    
    #Trigger 2 - toggle digital output 2 based on distance interval
    stage_handler.generic_command("trigger 2 when 1 dist {}".format(STAGE_ONE_TURN_STEPS // (2 * triggers_per_round)))
    stage_handler.generic_command("trigger 2 action a io set do 2 t")
    stage_handler.generic_command("trigger 2 enable")
    
    
    stage_handler.generic_command("trigger 4 when 1 pos == 0")
    stage_handler.generic_command("trigger 4 action a io set do 2 1")
    stage_handler.generic_command("trigger 4 enable")
    
    device_list = stage_handler.detect_devices()
    device = device_list[0]
    axis = device.get_axis(1)
    axis.home()
    
    warning_flags = axis.warnings.get_flags()
    if WarningFlags.CONTROLLER_TEMPERATURE_HIGH in warning_flags:
        print("Device is overheating!")
    else:
        temperature = stage_handler.generic_command("get driver.temperature").data
        print("The current temperature of the stage is {} °C\nIt is recommended that the temperature is below 80 °C\n".format(temperature))
    
    
    return axis
    
    
def print_TVAM(axis, dmd, printing_parameters):
    
    """
   Print using the TVAM process.

   Args:
       axis: The axis object of the stage.
       dmd: The DMD object.
       printing_parameters (argparse.Namespace): Parsed command-line arguments.
   """
    #axis.move_velocity(printing_parameters.velocity, unit=Units.ANGULAR_VELOCITY_DEGREES_PER_SECOND)

    dmd.Run()

    # move stage to an absolute position, this command is non-block, so it moves to the next line
    axis.move_absolute(STAGE_ONE_TURN_STEPS * (printing_parameters.num_turns + 1) - 1, Units.NATIVE, 
                       False, 
                       printing_parameters.velocity, Units.ANGULAR_VELOCITY_DEGREES_PER_SECOND)
        
    try:
        position = axis.get_position(unit=Units.NATIVE)
        with tqdm.tqdm(total = 360, desc = "Acceleratinggggg, print after 360°", bar_format= '{l_bar}{bar}{r_bar}') as pbar:
            while position < STAGE_ONE_TURN_STEPS:
                position = axis.get_position(unit=Units.NATIVE)
                if position < STAGE_ONE_TURN_STEPS:
                    pbar.update(int(position / STAGE_ONE_TURN_STEPS * 360) - pbar.n)
        
        

        with tqdm.tqdm(total = 360 * printing_parameters.num_turns, desc = "Printinggggg", bar_format= '{l_bar}{bar}{r_bar}') as pbar:
            while position < STAGE_ONE_TURN_STEPS * (1 + printing_parameters.num_turns) - 1:
                position = axis.get_position(unit=Units.NATIVE)
                pbar.update(int(position / STAGE_ONE_TURN_STEPS * 360) - pbar.n - 360)
                
        stop_dmd_stage(axis, dmd)

    except KeyboardInterrupt:
        print("Keyboard interrupt. Homing stage and stop.")
        stop_dmd_stage(axis, dmd)
    print("Print over, inspect sample")
    
    return


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

    dmd.SeqAlloc(nbImg = images.shape[0], bitDepth = 8)
    # Send the image sequence as a 1D list/array/numpy array
    print("We are loading {} images onto the DMD.".format(len(images)))
    dmd.SeqPut(imgData = images)  
    frequency_image = printing_parameters.velocity / 360 * images.shape[0]
    pictureTime = (1 / frequency_image)
    
    assert (frequency_image < 290), ("DMD can only do 290Hz with 8Bit grayscale. Choose a lower velocity, you tried to do {:.1f}Hz".format(frequency_image))
    
    # we subtract 50µs, if pictureTime is longer than the time between two triggers, no new image is shown
    dmd.SetTiming(pictureTime = round(pictureTime * 1_000_000) - 50)
    dmd.ProjControl(ALP_PROJ_MODE, ALP_SLAVE)
    dmd.DevControl(ALP_TRIGGER_EDGE, ALP_EDGE_RISING)
    print("Done setting up DMD and images are loaded.\n")
    return dmd, images.shape[0]



def load_images_and_correct_rotation_axis_wobbling(printing_parameters):

    """
    Shape images and apply wobbling/ordering/flip corrections
    
    Returns:
        numpy array: 2D array where the first dimension is images
    """
    
    print("Start loading images into RAM.")
    filelist = os.listdir(printing_parameters.path)
    filelist = sorted(filelist)
    images = []
    for i in tqdm.tqdm(filelist):
        image = os.path.join(printing_parameters.path, i)
        images.append(np.asarray(Image.open(image).convert('L')))
        
    print("The detected image shape is {}".format(images[0].shape))
    
    images = np.array(images)
    if printing_parameters.reverse_angles:
        print("Reverse angular order images")
        images = images[::-1, :, :]

    if printing_parameters.flip_vertical:
        print("Flip vertical axis of images.")
        images = images[:, :, ::-1]

    assert (images.shape[1] == 768 and images.shape[2] == 1024), "Image size is not 768 x 1024"
    

    if printing_parameters.amplitude == 0 and printing_parameters.phase == 0:
        print()
        return images.reshape(images.shape[0], -1)
    
    angles = np.linspace(0, 2 * np.pi, images.shape[0], endpoint=False)
    
    
    print("\nApply wobbling correction:")
    for i in tqdm.tqdm(range(images.shape[0])):
        φ = angles[i]
        shift_value = round(printing_parameters.amplitude * np.sin(φ + 
                                                                 printing_parameters.phase / 360 * 2 * np.pi))
        images[i, :, :] = np.roll(images[i, :, :], int(np.round(shift_value)), axis=0)
    
    print()
    return images.reshape(images.shape[0], -1)


print(WELCOME)
printing_parameters = process_arguments()
images = load_images_and_correct_rotation_axis_wobbling(printing_parameters)
dmd, num_of_images = initialize_DMD(images, printing_parameters)
axis_stage = initialize_stage(printing_parameters, triggers_per_round=num_of_images)
print_TVAM(axis_stage, dmd, printing_parameters)