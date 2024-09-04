# -*- coding: utf-8 -*-
"""
Created on Wed Jul 31 13:51:11 2024

@author: adminlapd
"""

# Importing the PIL library
from PIL import Image
from PIL import ImageDraw
import numpy as np

from PIL import ImageFont


for i in range(100):
    img = np.zeros((768, 1024))
    
    #img[768 // 2 -1 :768 // 2 + 2 , :] = 255
    # Open an Image 
    img = Image.fromarray(img).convert("L")
     
    # Call draw Method to add 2D graphics in an image
    I1 = ImageDraw.Draw(img)
    
    font = ImageFont.truetype("arial", 600)
    
    
    # Add Text to an image
    I1.text((358, 36), "{:02}".format(i), 255, font=font)
     
    # Display edited image

    
    img = np.array(img) > 0

    img = np.invert(img)
    img = Image.fromarray(img).convert("L")
    # Save the edited image
    img.save("images_100/{:04}.png".format(i))