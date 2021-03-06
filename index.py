#!/usr/bin/python3
# coding=utf8
import sys
sys.path.append('/home/pi/TonyPi/')
import cv2
import math
import time
import Camera
import threading
import numpy as np
from LABConfig import *
import HiwonderSDK.Misc as Misc
import HiwonderSDK.Board as Board
import HiwonderSDK.ActionGroupControl as AGC
import HiwonderSDK.TTS as TTS
import requests

# 人脸检测

if sys.version_info.major == 2:
    print('Please run this program with python3!')
    sys.exit(0)

# 阈值
conf_threshold = 0.6

# 表情识别接口
url = "http://192.168.83.19:5000/emotion"

# 模型位置
modelFile = "/home/pi/TonyPi/models/res10_300x300_ssd_iter_140000_fp16.caffemodel"
configFile = "/home/pi/TonyPi/models/deploy.prototxt"
net = cv2.dnn.readNetFromCaffe(configFile, modelFile)

#语音模块
tts = TTS.TTS()

servo2_pulse = servo2
# 初始位置
def initMove():
    Board.setPWMServoPulse(1, 1800, 500)
    Board.setPWMServoPulse(2, servo2_pulse, 500)

d_pulse = 10
start_greet = False
action_finish = True
# 变量重置
def reset():
    global d_pulse
    global start_greet
    global servo2_pulse    
    global action_finish

    d_pulse = 10
    start_greet = False
    action_finish = True
    servo2_pulse = servo2    
    initMove()  
    
# app初始化调用
def init():
    print("FaceDetect Init")
    reset()

__isRunning = False
# app开始玩法调用
def start():
    global __isRunning
    __isRunning = True
    print("FaceDetect Start")

# app停止玩法调用
def stop():
    global __isRunning
    __isRunning = False
    reset()
    print("FaceDetect Stop")

# app退出玩法调用
def exit():
    global __isRunning
    __isRunning = False
    AGC.runActionGroup('stand_slow')
    print("FaceDetect Exit")

def move():
    global start_greet
    global action_finish
    global d_pulse, servo2_pulse    
    
    while True:
        if __isRunning:
            if start_greet:
                start_greet = False
                action_finish = False
                AGC.runActionGroup('wave') # 识别到人脸时执行的动作
                action_finish = True
                time.sleep(0.5)
            else:
                if servo2_pulse > 2000 or servo2_pulse < 1000:
                    d_pulse = -d_pulse
            
                servo2_pulse += d_pulse       
                Board.setPWMServoPulse(2, servo2_pulse, 50)
                time.sleep(0.05)
        else:
            time.sleep(0.01)
            
# 运行子线程
th = threading.Thread(target=move)
th.setDaemon(True)
th.start()

size = (320, 240)
def run(img):
    global start_greet
    global action_finish
       
    img_copy = img.copy()
    img_h, img_w = img.shape[:2]

    if not __isRunning:
        return img

    blob = cv2.dnn.blobFromImage(img_copy, 1, (150, 150), [104, 117, 123], False, False)
    net.setInput(blob)
    detections = net.forward() #计算识别
    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence > conf_threshold:
            #识别到的人了的各个坐标转换会未缩放前的坐标
            x1 = int(detections[0, 0, i, 3] * img_w)
            y1 = int(detections[0, 0, i, 4] * img_h)
            x2 = int(detections[0, 0, i, 5] * img_w)
            y2 = int(detections[0, 0, i, 6] * img_h)             
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2, 8) #将识别到的人脸框出
            if((x2-x1) >= 100 and (y2-y1) >= 100):
              saveimg = img[y1:y2,x1:x2]
              gray=cv2.cvtColor(saveimg,cv2.COLOR_BGR2GRAY)
              resized = cv2.resize(gray, (48,48), interpolation = cv2.INTER_AREA)
              cv2.imwrite("test.jpg",resized)
              files = {'image': ('test.jpg', open('test.jpg', 'rb'))}
              r= requests.post(url, files=files)
              print(r.json())
              tts.TTSModuleSpeak('[h0][v10][m3]', r.json()['emotion'][0])
            if abs((x1 + x2)/2 - img_w/2) < img_w/4:
                if action_finish:
                    start_greet = True
    
    return img

if __name__ == '__main__':
    from CameraCalibration.CalibrationConfig import *
    
    #加载参数
    param_data = np.load(calibration_param_path + '.npz')

    #获取参数
    mtx = param_data['mtx_array']
    dist = param_data['dist_array']
    newcameramtx, roi = cv2.getOptimalNewCameraMatrix(mtx, dist, (640, 480), 0, (640, 480))
    mapx, mapy = cv2.initUndistortRectifyMap(mtx, dist, None, newcameramtx, (640, 480), 5)    
    
    init()
    start()
    my_camera = Camera.Camera()
    my_camera.camera_open()
    AGC.runActionGroup('stand')
    while True:
        img = my_camera.frame
        if img is not None:
            frame = img.copy()
            frame = cv2.remap(frame, mapx, mapy, cv2.INTER_LINEAR)  # 畸变矫正
            Frame = run(frame)           
            cv2.imshow('Frame', Frame)
            key = cv2.waitKey(1)
            if key == 27:
                break
        else:
            time.sleep(0.01)
    my_camera.camera_close()
    cv2.destroyAllWindows()
