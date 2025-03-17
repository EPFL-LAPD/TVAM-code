# -*- coding: utf-8 -*-
"""
Created on Wed Jul 31 13:51:11 2024

@author: adminlapd
"""

# Importing the PIL library
from PIL import Image
from PIL import ImageDraw
import numpy as np
import tqdm
from PIL import ImageFont

img = np.zeros((768, 1024))

on = False
for i in range(768 // 4):
    for j in range(1024):
        img[i, j] = 255 * on 
        on = not on
    on = not on

on = False
factor = 2

img = np.zeros((768, 1024))
for i in range(768 // factor):
    for j in range(1024 // factor):
        img[factor*i:factor*i+(factor), factor*j:factor*j+(factor)] = 255 * on 
        on = not on
    on = not on

img = Image.fromarray(img).convert("L")
img.save("checkerboard_{}x{}.png".format(factor, factor))




exit()
for i in tqdm.tqdm(range(1)):
    img = np.zeros((768, 1024)) + 255
    
    img[768 // 2 -1 :768 // 2 + 2 , :] = 0
    img[768 // 2 -1 -20:768 // 2 + 2 -20, :] = 0
    img[768 // 2 -1 +20:768 // 2 + 2 +20, :] = 0

    img[768 // 2 -1 -50:768 // 2 + 2 -50, :] = 0
    img[768 // 2 -1 +50:768 // 2 + 2 +50, :] = 0

    img[768 // 2 -1 -100:768 // 2 + 2 -100, :] = 0
    img[768 // 2 -1 +100:768 // 2 + 2 +100, :] = 0

    # Open an Image 
    img = Image.fromarray(img).convert("L")
     
    # Call draw Method to add 2D graphics in an image
    #I1 = ImageDraw.Draw(img)
    
    #font = ImageFont.truetype("arial", 600)
    
    
    # Add Text to an image
    #I1.text((358, 36), "{:02}".format(i), 255, font=font)
     
    # Display edited image

    
    #img = np.array(img) > 0

    #img = np.invert(img)
    #img = Image.fromarray(img).convert("L")
    # Save the edited image
    img = np.zeros((768, 1024))
    #img[100:-100, 100:-100] = 255
    img[120:648, 200:800] = 255
    img = Image.fromarray(img).convert("L")
    img.save("croped_120_648_200_800.png")
    #img.save("images_white/{:04}.png".format(i))