import cv2
import os
import io
import threading
import queue
import time
import base64
from PIL import Image
from datetime import date
from flask_cors import CORS
from models import DetectObject
from flask import Flask, render_template, request, jsonify, Response, send_file
from supervision.geometry.dataclasses import Point

app = Flask(__name__)
# CORS(app)

VIDEO_FOLDER = '/project/backend/videos/'
video_capture = None
video_lock = threading.Lock()
max_size_frame = 60
frame_store = queue.Queue(maxsize=max_size_frame)
processing_thread = None
current_video = None
current_frame = 0
fps = 60
total_frames = 0
stop_processing = threading.Event()
run = True
video_path = ""
 
# Object use for detect object
detector = DetectObject("/project/backend/models/trainedmodels/yoloDetect_x.pt", "/project/backend/models/trainedmodels/mobilenetV3Config.pt", Point(5, 5), Point(5, 5))


# Producer thread: read & process frames
def frame_producer(videopath, start_frame=0):
    global video_capture, frame_store, fps, total_frames, stop_processing, video_path
    video_capture = cv2.VideoCapture(videopath)
    video_capture.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    total_frames = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = video_capture.get(cv2.CAP_PROP_FPS)
    video_path = videopath
    
    while not stop_processing.is_set():
        if frame_store.full():
            time.sleep(0.01)
            continue

        ret, frame = video_capture.read()
        if not ret:
            break
            
        if stop_processing.is_set():
            break
        
        # Detect part
        frame = detector.detect_frame(frame)

        while (True):
            try:
                frame_store.put(frame, timeout=0.1)
                break
            except queue.Full:
                pass

    video_capture.release()

# Serve main page
@app.route('/')
def index():
    with open('/project/backend/video_list.txt', 'r') as f:
        videos = [line.strip() for line in f.readlines()]
    # Can edit to show only some video
    # videos = ['video_CH05.mp4']

    return render_template('chefops.html', videos=videos)


# Load video and start processing thread
@app.route('/load_video', methods=['POST'])
def load_video():
    global fisrt_run, processing_thread, frame_store, current_frame, current_video
    
    video_name = request.json['video']
    video_path = os.path.join(VIDEO_FOLDER, video_name)
    current_video = video_path

    # Stop previous thread if running
    stop_processing.set()
    if processing_thread and processing_thread.is_alive():
        processing_thread.join(timeout=0.1) 

    stop_processing.clear()

    # reset in out objects
    detector.reset_params()

    # reset frame_store (better read it to end)
    frame_store = queue.Queue(maxsize=max_size_frame)
    current_frame = 0

    # Start new thread
    processing_thread = threading.Thread(target=frame_producer, args=(video_path, 0))
    processing_thread.daemon = True
    processing_thread.start()
    return jsonify({'status': 'loaded'})
    

# Helper: Restart processing thread at specific frame
def restart_processing_at(seek_frame):
    global processing_thread, stop_processing, frame_store

    stop_processing.set()
    
    if processing_thread and processing_thread.is_alive():
        processing_thread.join()

    stop_processing.clear()

    # reset in out objects
    detector.reset_params()

    # reset frame_store (better read it to end)
    frame_store = queue.Queue(maxsize=max_size_frame)

    processing_thread = threading.Thread(target=frame_producer, args=(current_video, seek_frame))
    processing_thread.daemon = True
    processing_thread.start()


@app.route('/get_frame', methods=['POST'])
def get_frame():
    global current_frame

    data = request.json
    if 'seek' in data:
        # Seek requested, restart thread
        seek_to = int(data['seek'])
        restart_processing_at(seek_to)
        current_frame = seek_to
    
    # if no processed frame then end this thread
    if frame_store.empty():
        return jsonify({'status': 'frame_store empty'})

    frame = frame_store.get()
    current_frame += 1
    _, jpeg = cv2.imencode('.jpg', frame)
    return Response(jpeg.tobytes(), mimetype='image/jpeg')

@app.route('/video_info', methods=['GET'])
def video_info():
    return jsonify({'total_frames': total_frames, 'fps': fps})

@app.route('/submit_button', methods=['POST'])
def process_button():
    data            = request.get_json()
    user            = data['userId']
    currentFrame    = data['currentFrame']
    err             = data['err']
    base64_data     = data['image']

    if not base64_data:
        return jsonify({'status': 'err base64_data empty'})
    
    image_bytes = base64.b64decode(base64_data)
    image = Image.open(io.BytesIO(image_bytes))
    video_name = video_path.split('/')[-1]
    image.save(f"/project/backend/feedback/img/{date.today()}_user{user}_video{video_name}_frame{currentFrame}.jpeg")  # Save or process
    with open(f"/project/backend/feedback/userfeedback/{date.today()}_user{user}_video{video_name}_frame{currentFrame}.txt", "w") as file:
        file.writelines(err)

    return jsonify({'status': 'saved'})

if __name__ == '__main__':
    # import logging
    # log = logging.getLogger('werkzeug')
    # log.disabled = True
    app.run(debug=True, host='0.0.0.0', port=8000, threaded=True)