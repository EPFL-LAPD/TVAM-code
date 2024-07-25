# -*- coding: utf-8 -*-
"""
Created on Wed Jun 19 15:21:28 2024

@author: adminlapd
"""

from zaber_motion.ascii import Connection
from zaber_motion import Units
import time
from zaber_motion.ascii import WarningFlags
from tqdm import tqdm


import os
import argparse
import numpy as np
from multiprocessing import Pool


def process_arguments():
  
    """
   Parse and process command-line arguments.

   Returns:
       argparse.Namespace: Parsed command-line arguments.
   """
    
    # Instantiate the parser
    parser = argparse.ArgumentParser(description='Optional app description')
    parser.add_argument('-s', '--step_angle', help="step angle in degree. 360/number_of_images, default is 0.36",
                        action="store", type=float, default=0.36)
    
    parser.add_argument('-v', '--velocity', help="rotation speed in deg/sec, default is 40.0",
                        action="store", type=float, default=40.0)
    
    parser.add_argument('-d', '--DMD_duty_cycle', help="DMD duty cycle, default is 0.99",
                        action="store", type=float, default=0.99)
    
    parser.add_argument('-n', '--num_turns', help="number of turns, default is 3",
                        action="store", type=int, default=3)
    
    parser.add_argument('-p', '--path', help="path to images, no default",
                        action="store")
    
    parser.add_argument('-ps', '--port_stage', help="port of the stage",
                        action="store", type=str, default="COM3")
    
    parser.add_argument('-a', '--amplitude', type=float, help="Amplitude of the sinusoidal wobble.")
    
    parser.add_argument('-ph', 'phase', type=float, help="Phase shift of the sinusoidal wobble.")
    
    #parser.parse_args(['-h'])
    args = parser.parse_args()
    assert args.DMD_duty_cycle < 1 and args.DMD_duty_cycle > 0.28
    assert args.velocity <= 80
    
    return args

    

def stop_dmd_stage(axis, dmd):
   
    """
   Stop the DMD and stage.

   Args:
       axis: The axis object of the stage.
       dmd: The DMD object.
   """
    
    try:
        #dmd.haltProj()
        #dmd.free()
        1+1
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
   
    stage_one_turn_steps = 384_000

    assert stage_one_turn_steps % (2 * triggers_per_round) ("{} has to be divisible by 2 * {}".format(stage_one_turn_steps, triggers_per_round))

    stage_handler = Connection.open_serial_port(printing_parameters.port_stage)
    
    warning_flags = stage_handler.warnings.get_flags()
    if WarningFlags.CONTROLLER_TEMPERATURE_HIGH in warning_flags:
        print("Device is overheating!")
    else:
        temperature = stage_handler.generic_command("get driver.temperature").data
        print("The current temperature is {}\n It is recommended that the temperature is below 80 °C").format(temperature)
    
        
    print("Initialize stage, initialize triggers and reset triggers to 0")
    # indicates the steps to turn one round on the stage")

    #Trigger 1 - Set digital output 1 == 1 when pos > 360°
    stage_handler.generic_command("system restore")
    # trigger when position >= 360°
    stage_handler.generic_command("trigger 1 when 1 pos >= {}").format(stage_one_turn_steps) 
    #set digital output 1 to 1
    stage_handler.generic_command('trigger 1 action a io set do 1 1')
    stage_handler.generic_command("trigger 1 enable")
    
    
    stage_handler.generic_command("trigger 3 when 1 pos < {}").format(stage_one_turn_steps)
    # when it is below <360°, set trigger hard to 0
    stage_handler.generic_command('trigger 3 action a io set do 1 0') 
    stage_handler.generic_command("trigger 3 enable")
    
    
    #Trigger 2 - toggle digital output 2 based on distance interval
    stage_handler.generic_command("trigger 2 when 1 dist {}".format(stage_one_turn_steps // (2 * triggers_per_round)))
    stage_handler.generic_command("trigger 2 action a io set do 2 t")
    stage_handler.generic_command("trigger 2 enable")
    
    device_list = stage_handler.detect_devices()
    device = device_list[0]
    axis = device.get_axis(1)
    axis.home()
    return axis
    
    
def print_TVAM(axis, dmd, printing_parameters):
    
    """
   Print using the TVAM process.

   Args:
       axis: The axis object of the stage.
       dmd: The DMD object.
       printing_parameters (argparse.Namespace): Parsed command-line arguments.
   """
    
    axis.move_velocity(printing_parameters.velocity, unit=Units.ANGULAR_VELOCITY_DEGREES_PER_SECOND)
    
    
    try:
        position = axis.get_position(unit=Units.ANGLE_DEGREES)
        with tqdm.tqdm(total = 360, desc = "Acceleratinggggg, print after 360°", bar_format= '{l_bar}{bar}{r_bar}') as pbar:
            while position < 360:
                position = axis.get_position(unit=Units.ANGLE_DEGREES)
                pbar.update(int(position)-pbar.n)
                
                
        # DMD.dmd.startContProj(name_of_sequences[0])
        with tqdm.tqdm(total = 360 * printing_parameters.num_turns, desc = "Printinggggg", bar_format= '{l_bar}{bar}{r_bar}') as pbar:
            while position < 360 + 360 * printing_parameters.num_turns:
                position = axis.get_position(unit=Units.ANGLE_DEGREES)
                pbar.update(int(position)-pbar.n - 360)
                
        stop_dmd_stage(axis, dmd)

    except KeyboardInterrupt:
        print("Keyboard interrupt. Homing stage and stop.")
        stop_dmd_stage(axis, dmd)
    print("Print over, inspect sample")
    
    return


def initialize_DMD():
    
    """
    Initialize the DMD.

    Returns:
        tuple: The DMD object and number of images.
    """
    
    #BASEDIR = r"D:/"
    #SINOGRAM_DIR = args.path 
    #IMAGE_DIRECTORY = os.path.join(SINOGRAM_DIR, '*.png')#

    return 0

def correct_rotation_axis_wobbling(patterns, angles, amplitude, phase):
    assert patterns.shape[1] == angles.shape[0], "Size mismatch between angles and patterns"
    patterns_out = np.copy(patterns)
    
    def process_column(i):
        φ = angles[i]
        shift_value = round(amplitude * np.sin(φ + phase))
        patterns_out[:, i, :] = np.roll(patterns[:, i, :], shift_value, axis=0)
    
    with Pool() as pool:
        pool.map(process_column, range(patterns.shape[1]))

    return patterns_out


printing_parameters = process_arguments()
dmd, num_of_images = initialize_DMD()
axis_stage = initialize_stage(printing_parameters, triggers_per_round=num_of_images)
print_TVAM(axis_stage, dmd, printing_parameters)