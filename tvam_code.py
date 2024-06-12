# -*- coding: utf-8 -*-
"""

@author: wechsler
adapted from very old code
"""
import os
import argparse

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

#parser.parse_args(['-h'])

args = parser.parse_args()
STEP_ANGLE = args.step_angle

VELOCITY = args.velocity
DMD_DUTY_CYCLE = args.DMD_duty_cycle
assert DMD_DUTY_CYCLE < 1 and DMD_DUTY_CYCLE > 0.28

assert VELOCITY <= 80
num_turns = args.num_turns
BASEDIR = r"D:/"
SINOGRAM_DIR = args.path 
IMAGE_DIRECTORY = os.path.join(SINOGRAM_DIR, '*.png')




# Imports 
from PIL import Image
import numpy as np
import sys
import time
import matplotlib.pyplot as plt

import matplotlib.pyplot as plt
import glob
import math

import nidaqmx
from nidaqmx.constants import TriggerType, Edge, AcquisitionType, TaskMode, LineGrouping
import nidaqmx.system
import collections
import os.path as osp
from PyDAQmx.DAQmxFunctions import *
from PyDAQmx.DAQmxConstants import *
from zaber_motion import Library
from zaber_motion.ascii import Connection
from zaber_motion import Units
from zaber_motion import Measurement
from zaber_motion.ascii import Response
from zaber_motion.ascii import DeviceSettings
from zaber_motion.ascii import SettingConstants

import sys
sys.path.append(r'D:\vialux')

from communication import DMD as communication
import tqdm


####### Parameters for PRINTING 
Nsat = 1 # W-ARNING: if not equal to 1 you change patterns intensity












# CONSTANTS
sys.path.append(IMAGE_DIRECTORY)

DATA_FORMAT = 0 

# continueous pulse class
class ContinuousPulseTrainGeneration():
    """ Class to create a continuous pulse train on a counter
    Usage:  pulse = ContinuousTrainGeneration(period [s],
                duty_cycle (default = 0.5), counter (default = "dev1/ctr0"),
                reset = True/False)"""
    def __init__(self, period=1., duty_cycle=0.5, counter="Dev1/ctr0", reset=False):
        if reset:
            DAQmxResetDevice(counter.split('/')[0])
        taskHandle = TaskHandle(0)
        DAQmxCreateTask("",byref(taskHandle))
        DAQmxCreateCOPulseChanFreq(taskHandle,counter,"",DAQmx_Val_Hz,DAQmx_Val_Low,
                                                                   0.0,1/float(period),duty_cycle)
        DAQmxCfgImplicitTiming(taskHandle,DAQmx_Val_ContSamps,1000)
        self.taskHandle = taskHandle
    def start(self):
        DAQmxStartTask(self.taskHandle)
    def stop(self):
        DAQmxStopTask(self.taskHandle)
    def clear(self):
        DAQmxClearTask(self.taskHandle)


# STAGE
def initializeStage(port_id):
    ''' Initialize the rotational stage, its axis and its settings from the name of the usb port (port_id)'''
    connection = Connection.open_serial_port(port_id)
    device_list = connection.detect_devices() # get list of connected zaber devices
    device = device_list[0]
    axis = device.get_axis(1) # get axis of device
    axis.home()
    device_settings = DeviceSettings(device)  # create instance for device settings
    
    return device, axis, device_settings, connection


def stage_setSpeedLims(device_settings, maxspeed=100, accel=10):
    device_settings.set(setting='maxspeed', value=maxspeed,
                        unit=Units.ANGULAR_VELOCITY_DEGREES_PER_SECOND)  # set maxspeed
    device_settings.set(setting='accel', value=accel,
                        unit=Units.ANGULAR_ACCELERATION_DEGREES_PER_SECOND_SQUARED)  # set accel


# DMD
MAX_IMAGES_MEMORY = 2730     #This is the maximum number of 8-bit images that can fit in DMD memory wrt to optimal timing etc
def import_bin_file():
    print("Importing images...")
    print("This might take a while...")
    images = np.fromfile("train_labelsF.bin",  dtype='B')
    nbr_of_images = int(len(images)/(1024*768))
    print(nbr_of_images, " images detected")
    number_of_packages = math.ceil(nbr_of_images / MAX_IMAGES_MEMORY)
    print("Number of packages needed: ", number_of_packages)
    list_of_seq = [None] * number_of_packages
    name_of_seq = [None] * number_of_packages
    for k in range(number_of_packages):
        name_of_seq[k] = 'seq' + str(k)
        k_seq = images[(k *(1024*768)* MAX_IMAGES_MEMORY):((k + 1)*(1024*768) * MAX_IMAGES_MEMORY)]
        print("Number of images in this packet is ", int(len(k_seq)/(1024*768)))
        list_of_seq[k] = k_seq
        print("Package", (k + 1), "over", number_of_packages, "completed")
        image_print = k_seq[(1024*768)*3:4*(1024*768)]
        image_print.resize(768,1024)
        imgagee = Image.fromarray(image_print)
        imgagee.save('table.png')

    return list_of_seq, name_of_seq, nbr_of_images

def compile_images(dmd, dmd_pattern):
    images = dmd_pattern.astype(np.uint8)
    nbr_of_images = int(len(images))
    print(nbr_of_images, " images detected")
    number_of_packages = math.ceil(len(images) / MAX_IMAGES_MEMORY)
    print("Number of packages needed: ", number_of_packages)
    list_of_seq = [None] * number_of_packages
    name_of_seq = [None] * number_of_packages
    for k in range(number_of_packages):
        name_of_seq[k] = 'seq' + str(k)
        k_seq = images[(k * MAX_IMAGES_MEMORY):((k + 1) * MAX_IMAGES_MEMORY)]
        print("Number of images in this packet is ", len(k_seq))
        # list_of_seq[k] = communication.compilePicture(k_seq, int(len(k_seq)))
        list_of_seq[k] = communication.compilePicturev2fast(dmd, k_seq)
        print("Package", (k + 1), "over", number_of_packages, "completed")

    return list_of_seq, name_of_seq, nbr_of_images


def import_and_compile_images(dmd, image_dir, Nsat):
    filelist = glob.glob(image_dir)
    print("Importing images...")
    print("This might take a while...")
    images = np.array([Nsat*np.array(Image.open(fname)) for fname in filelist], dtype=np.uint8)
    # images = np.array([np.array(Image.open(fname)) for fname in filelist], dtype=np.uint8) * mask
    # images = np.uint8(images)
    nbr_of_images = int(len(images))
    print(nbr_of_images, " images detected")
    number_of_packages = math.ceil(len(images) / MAX_IMAGES_MEMORY)
    print("Number of packages needed: ", number_of_packages)
    list_of_seq = [None] * number_of_packages
    name_of_seq = [None] * number_of_packages
    for k in range(number_of_packages):
        name_of_seq[k] = 'seq' + str(k)
        k_seq = images[(k * MAX_IMAGES_MEMORY):((k + 1) * MAX_IMAGES_MEMORY)]
        print("Number of images in this packet is ", len(k_seq))
        # list_of_seq[k] = communication.compilePicture(k_seq, int(len(k_seq)))
        list_of_seq[k] = communication.compilePicturev2fast(dmd, k_seq)
        print("Package", (k + 1), "over", number_of_packages, "completed")

    return list_of_seq, name_of_seq, nbr_of_images

def save_experiment_parameters(parameters_out):
    with open(parameters_out["file_name"], 'w') as f:
        print("electrodes_sampling_freq[Hz]: ", parameters_out["electrodes_sampling_freq[Hz]"], file=f)
        print("trigger_freq[Hz]: ", parameters_out["trigger_freq[Hz]"], file=f)
        print("trigger_Thigh[us]: ", parameters_out["trigger_Thigh[us]"], file=f)
        print("trigger_Tlow[us]: ", parameters_out["trigger_Tlow[us]"], file=f)
        print("images_directory: ", parameters_out["images_directory"], file=f)
        print("DMD_Picture_time[us]: ", parameters_out["DMD_Picture_time[us]"], file=f)
        print("nbr_of_images: ", parameters_out["nbr_of_images"], file=f)
    print("Data of this packet saved")


#########################9###################

# Initialize Digital Micromirror Device (DMD)
dmd = communication()

# Load patterns to DMD

# DMD parameters. No need to modify them
parameters = dict()
parameters["electrodes_sampling_freq[Hz]"] = 10000
parameters["trigger_freq[Hz]"] = VELOCITY/STEP_ANGLE
parameters["images_directory"] = IMAGE_DIRECTORY
dmd_on_time = 1/parameters["trigger_freq[Hz]"]*1e6
parameters["DMD_Picture_time[us]"] = DMD_DUTY_CYCLE*dmd_on_time

if parameters["DMD_Picture_time[us]"] > (1/parameters["trigger_freq[Hz]"])*1e6:
    print("DMD picture time bigger than T not possible")
    print("The program will close")
    input("Press enter to close the program...")
    sys.exit()

list_of_sequences, name_of_sequences, parameters["nbr_of_images"] = import_and_compile_images(dmd, IMAGE_DIRECTORY, Nsat)
nbr_of_packets = int(len(list_of_sequences))

nbr_images_in_this_packet = int(len(list_of_sequences[0])/(768*1024))

# configuration of the DMD with the wanted parameters
dmd.controlProj('ALP_PROJ_MODE', 'ALP_SLAVE')
dmd.controlDev('ALP_EDGE_RISING')

print("Starting loading image")
start_loading = time.time()
dmd.allocSeq(name_of_sequences[0], nbr_images_in_this_packet, 
             data_format=DATA_FORMAT)
dmd.putSeq(name_of_sequences[0], list_of_sequences[0])
print("The transfer took", (time.time()-start_loading), "seconds")
print("All images loaded")
dmd.timingSeq(name_of_sequences[0], int(parameters["DMD_Picture_time[us]"]))

# Initialize STAGE and DAQ
 
# Initialize stage
stage, axis, stage_settings, connection = initializeStage(port_id='COM4')
maxspeed = 100
accel = 3 + VELOCITY / 80 * 17
stage_setSpeedLims(stage_settings, maxspeed, accel)

time.sleep(5)

# initialize DAQ
system = nidaqmx.system.System.local()
system.driver_version
for device in system.devices:
    print(device)
          
isinstance(system.devices, collections.Sequence)     

daq = system.devices['Dev1']
daq == nidaqmx.system.Device('Dev1')

# DEFINE DAQ LINES
laser_line = 'Dev1/port2/line4'
dmd_trigger_line = "Dev1/ctr1"

# PRINT
# 1. set stage to movement at steady speed
pos_initial = axis.get_position(unit=Units.ANGLE_DEGREES)

t_acceleration = 5
t_0 = time.time()
t_measure_speed_0 = t_0 + t_acceleration
t_measure_speed_end = t_measure_speed_0 + 3

times = []
positions = []

#num_turns = input("number of turns to print: \n")

t_rot = float(num_turns)*360/VELOCITY

# 3. send triggers to DMD
dmd_trig_period = 1/parameters["trigger_freq[Hz]"]
pulse_DMD = ContinuousPulseTrainGeneration(period=dmd_trig_period, 
                                           duty_cycle=0.2,
                                           counter=dmd_trigger_line, 
                                           reset=True)

# Start the DMD, it will wait for a trigger comming from the stimulus generator
# Create task for lasers
# 2. Turn lasers on
#task_lasers = nidaqmx.Task()
#task_lasers.do_channels.add_do_chan(laser_line)
#task_lasers.start()
#task_lasers.write(data=True, auto_start=True, timeout=10)
#print("lasers are ON")


#time.sleep(t_acceleration)

axis.move_velocity(VELOCITY, unit=Units.ANGULAR_VELOCITY_DEGREES_PER_SECOND)

position = axis.get_position(unit=Units.ANGLE_DEGREES)

with tqdm.tqdm(total = 360, desc = "Acceleratinggggg", bar_format= '{l_bar}{bar}{r_bar}') as pbar:
    while position < 360:
        position = axis.get_position(unit=Units.ANGLE_DEGREES)
        pbar.update(int(position)-pbar.n)
    

t_dmd = time.time()
dmd.startContProj(name_of_sequences[0])
pulse_DMD.start()
print("DMD is being triggered")

print("")
ti = 0
t0 = time.time()
ti = t0
ti0 = t0
fac = 100
nb_bloc = 50

try:
    while ti < t0+t_rot:
        ti = time.time()
        tii = ti
        if tii > ti0+t_rot/fac:
            sys.stdout.write('\r')
            i = np.floor((ti-t0)/t_rot*nb_bloc)
            i = int(i)
            sys.stdout.write("[%-49s] %d%%" % ('■'*i, (i+1)*fac/nb_bloc))  # 49 = nb_bloc-1
            sys.stdout.flush()
            ti0 = tii
except KeyboardInterrupt:
    pass
        
print("")


# Stop the display of the sequence.
dmd.haltProj()
pulse_DMD.stop()
pulse_DMD.clear()

print("DMD stopped")
dmd.freeSeq(name_of_sequences[0])
# stop the stage
axis.stop()
pos_final = axis.get_position(unit=Units.ANGLE_DEGREES)
axis.home()
print("stage is home")

displacement = pos_final - pos_initial
print('displacement : {0:.2f}  deg'.format(displacement))
print("")
print('Print TIME = : {0:.2f}  s'.format(ti-t0))
print('Percentage = : {0:.2f}  '.format(((ti-t0)/t_rot)*100))
print('Nb_turns = : {0:.2f} '.format((ti-t0)/360*VELOCITY))

# Free DMD Sequence
#dmd.freeSeq(name_of_sequences[0])
dmd.free()


