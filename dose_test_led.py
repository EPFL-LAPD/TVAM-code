import numpy as np
import argparse
from PIL import Image
from ALP4 import *
import time
from tqdm import tqdm
import sys


parser = argparse.ArgumentParser(description='Simple dose test with a grid of 5x5')
parser.add_argument('--exposure_time', help="exposure time in seconds",
                        action="store")
parser.add_argument('--square_width', help="width of each square",
                        action="store", default=20)
parser.add_argument('--spacing', help="spacing between the squares",
                        action="store", default=50)
parser.add_argument('--background_intensity', help="background",
                        action="store", default=0)

parser.add_argument('-f', "--flat_field", action = 'store', help = "Flat field correction image for DMD. DMD is divided by this", type=str, default = "None")


# this script displays an image on the DMD until the user interrupts.
# usage: python dmd_show_image.py image.png
DMD = ALP4(version = '4.3', libDir=".")
# Initialize the device
DMD.Initialize()

printing_parameters = parser.parse_args()
exposure_time = float(printing_parameters.exposure_time)

# Create a blank 1024x768 array
img = int(printing_parameters.background_intensity) + np.zeros((500, 500), dtype=np.uint8)

# Parameters

square_width = int(printing_parameters.square_width)
spacing = int(printing_parameters.spacing)
n = 5  # 5x5 grid

# Calculate starting positions
start_x = (500 - (n * square_width + (n - 1) * spacing)) // 2
start_y = (500 - (n * square_width + (n - 1) * spacing)) // 2

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


images = img


flat_field = Image.open(printing_parameters.flat_field).convert('L')
flat_field = np.array(flat_field)
flat_field = np.array(flat_field, dtype=float).reshape(flat_field.shape[0], flat_field.shape[1])

flat_field /= np.max(flat_field)
flat_field_inv = 1 / flat_field
flat_field_inv /= np.max(flat_field_inv)
images = np.array(images, dtype=float) * flat_field_inv**1.15
images = np.array(images / np.max(images) * 255, dtype=np.uint8)



print("Pad the images")
images_n = np.zeros((768, 1024))
height = images.shape[0] // 2
width = images.shape[1] // 2
images_n[768 // 2 - height:768//2+height, 1024 // 2 - width : 1024 // 2 + width] = images
images = images_n 

img = images

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

    with tqdm(
        total=exposure_time,
        unit="s",
        desc="Exposure",
        bar_format="{l_bar}{bar}| {n:.2f}s/{total:.2f}s"
    ) as pbar:
        start_time = time.time()
        end_time = start_time + exposure_time

        while time.time() < end_time:
            elapsed = time.time() - start_time
            pbar.n = elapsed
            pbar.refresh()
            time.sleep(0.1)

    print("\nDone!")
    DMD.Halt()
    DMD.FreeSeq()
    DMD.Free()

except KeyboardInterrupt:
    # Stop the sequence display
    DMD.Halt()
    # Free the sequence from the onboard memory
    DMD.FreeSeq()
    # De-allocate the device
    DMD.Free()