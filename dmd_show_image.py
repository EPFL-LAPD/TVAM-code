
from ALP4 import *
from PIL import Image
import sys
import time 
import pyexr
import matplotlib.pyplot as plt
import os
# this script displays an image on the DMD until the user interrupts.
# usage: python dmd_show_image.py image.png
DMD = ALP4(version = '4.3', libDir=".")
# Initialize the device
DMD.Initialize()


#img = np.asarray(Image.open(sys.argv[1]).convert('L'))
os.environ["OPENCV_IO_ENABLE_OPENEXR"]="1"

import cv2
img = cv2.imread(sys.argv[1],  cv2.IMREAD_ANYCOLOR | cv2.IMREAD_ANYDEPTH)

print(np.max(img))
print(np.min(img))

#img = np.transpose(np.array(img / np.max(img) * 255, dtype=np.uint8))[:, ::-1]

img = np.array(img / np.max(img) * 255, dtype=np.uint8)
print(np.max(img))
print(np.min(img))

try:
	imgSeq  = np.concatenate([img.ravel()])
	# Allocate the onboard memory for the image sequence
	DMD.SeqAlloc(nbImg = 1, bitDepth = 8)
	# Send the image sequence as a 1D list/array/numpy array
	DMD.SeqPut(imgData = imgSeq)
	# Set image rate to 50 Hz
	DMD.SetTiming(pictureTime = 10000)
	# Run the sequence in an infinite loop
	DMD.Run()
	time.sleep(10000000)
except KeyboardInterrupt:
	# Stop the sequence display
	DMD.Halt()
	# Free the sequence from the onboard memory
	DMD.FreeSeq()
	# De-allocate the device
	DMD.Free()