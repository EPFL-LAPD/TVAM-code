import numpy as np
import argparse
from PIL import Image
from ALP4 import *
import time



parser = argparse.ArgumentParser(description='Simple dose test with a grid of 5x5')
parser.add_argument('--exposure_time', help="exposure time in seconds",
                        action="store")
parser.add_argument('--square_width', help="width of each square",
                        action="store", default=20)
parser.add_argument('--spacing', help="spacing between the squares",
                        action="store", default=50)
parser.add_argument('--background_intensity', help="background",
                        action="store", default=0)

# this script displays an image on the DMD until the user interrupts.
# usage: python dmd_show_image.py image.png
DMD = ALP4(version = '4.2')
# Initialize the device
DMD.Initialize()

printing_parameters = parser.parse_args()
exposure_time = int(printing_parameters.exposure_time)

# Create a blank 1024x768 array
img = int(printing_parameters.background_intensity) + np.zeros((768, 1024), dtype=np.uint8)

# Parameters

square_width = int(printing_parameters.square_width)
spacing = int(printing_parameters.spacing)
n = 5  # 5x5 grid

# Calculate starting positions
start_x = (1024 - (n * square_width + (n - 1) * spacing)) // 2
start_y = (768 - (n * square_width + (n - 1) * spacing)) // 2

# Fill squares with increasing intensity
intensity = 10
for i in range(n):
    for j in range(n):
        x = start_x + j * (square_width + spacing)
        y = start_y + i * (square_width + spacing)
        img[y:y+square_width, 
            x:x+square_width] = 5 + intensity
        intensity += 10

# Now `img` is your desired array
img = np.flipud(img)

# Assuming `img` is your 1024x768 NumPy array
img_pil = Image.fromarray(img)
img_pil.save("dose_test.png")


try:
    imgSeq  = np.concatenate([img.ravel()])
    # Allocate the onboard memory for the image sequence
    DMD.SeqAlloc(nbImg = 1, bitDepth = 8)
    # Send the image sequence as a 1D list/array/numpy array
    DMD.SeqPut(imgData = imgSeq)
    # picture time in microseconds
    DMD.SetTiming(pictureTime = 4_000)
    # Run the sequence in an infinite loop
    DMD.Run()
    import sys

# show progress during exposure
    for i in range(exposure_time):
        percent = (i + 1) / exposure_time * 100
    # overwrite the same line in terminal
        sys.stdout.write(f"\rProgress: {percent:.0f}%")
        sys.stdout.flush()
        time.sleep(1)
    print("\nDone!")
    # time.sleep(exposure_time)
    DMD.Halt()
    # Free the sequence from the onboard memory
    DMD.FreeSeq()
    # De-allocate the device
    DMD.Free() 
except KeyboardInterrupt:
    # Stop the sequence display
    DMD.Halt()
    # Free the sequence from the onboard memory
    DMD.FreeSeq()
    # De-allocate the device
    DMD.Free()