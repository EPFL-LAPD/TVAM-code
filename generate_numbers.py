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


for i in range(1000):
    img = np.zeros((768, 1024))
    
    # Open an Image
    img = Image.fromarray(img).convert("L")
     
    # Call draw Method to add 2D graphics in an image
    I1 = ImageDraw.Draw(img)
    
    font = ImageFont.truetype("arial", 300)
    
    
    # Add Text to an image
    I1.text((28, 36), "{:04}".format(i), 255, font=font)
     
    # Display edited image
    
     
    # Save the edited image
    img.save("images_1000/{:04}.png".format(i))