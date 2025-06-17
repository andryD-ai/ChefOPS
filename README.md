# ChefOps - Chef Operations Architecture

This is a simple detecting and tracking Food web app in dispenser area in kitchen of a restaurant.

![Detection and tracking in restaurants](./img_readme/detect1.jpeg)

### 🔧 Components
- Python (Flask, OpenCV, threading)
- JavaScript (vanilla JS + HTML)
- YOLOv5 + MobileNetV3
- Base64 image transfer + annotation
- Feedback system with image + text

## System model

### Web Diagram

+-------------------------+       HTTP/JSON        +------------------------+
|     Web Browser (JS)    | <--------------------> |    Flask Backend API    |
|-------------------------|                        |------------------------|
| - Select video          |   /load_video (POST)   | - Starts processing    |
| - View annotated frame  |   /get_frame (POST)    | - Detect objects       |
| - Seek slider           |   /video_info (GET)    | - Queue frames         |
| - Submit feedback       |   /submit_button (POST)| - Save feedback/images |
+-------------------------+                        +------------------------+
                                                          |
                                                          v
                                                 +---------------------+
                                                 |  Frame Producer     |
                                                 |  (Threaded, OpenCV) |
                                                 +---------------------+
                                                          |
                                                          v
                                                +----------------------+
                                                |  Object Detection    |
                                                |  YOLO + MobileNetV3  |
                                                +----------------------+
                                                          |
                                                          v
                                                +----------------------+
                                                | Frame Queue (Buffer) |
                                                +----------------------+
                                                          |
                                                          v
                                                +----------------------+
                                                |  Feedback Saver      |
                                                |  (Image & .txt file) |
                                                +----------------------+



## System configuration

The system is built under Kali Linux operating system.
Hardware is supported by NVIDIA GeForce GTX 1060 6GB. 
Driver Version: 535.247.01. CUDA Version: 12.2.

If you run on another operating system, you may need to install the system so that CUDA can support the YOLO model and MobileNet-v3-Large.

If running on CPU only, you may encounter lag problems

## Setting

|-- /get_frame reads frame from Queue
|-- /submit_button saves feedback (image + text)
|
v
[Disk Storage]
├─ feedback/img/.jpeg
└─ feedback/userfeedback/.txt

### 🧠 AI Architecture: Object Detection & Tracking

[Input Frame]
|
v
[YOLO Model]
(Object Detection)
|
v
[Bounding Boxes]
|
v
[MobileNetV3 Model]
(Optional Classification / Refinement)
|
v
[Annotated Frame with Detections]


## System configuration

The system is built under Kali Linux operating system.
Hardware is supported by NVIDIA GeForce GTX 1060 6GB. 
Driver Version: 535.247.01. CUDA Version: 12.2.

If you run on another operating system, you may need to install the system so that CUDA can support the YOLO model and MobileNet-v3-Large.

If running on CPU only, you may encounter lag problems

## Setting