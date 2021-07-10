import requests
import base64
import json

url = "http://192.168.83.19:5000/emotion"

import numpy as np
from PIL import Image
 
img = Image.open('ball.jpg')
img_convert_ndarray = np.array(img)
ndarray_convert_img= Image.fromarray(img_convert_ndarray )
# files = {'image': ('ball.jpg', open('ball.jpg', 'rb'))}
files = {'image': ('ball.jpg', img_convert_ndarray)}
r= requests.post(url, files=files)
print(r.json())