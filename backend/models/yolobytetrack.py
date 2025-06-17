import os
import cv2
import torch
import ultralytics
import numpy as np
from typing import List
from ultralytics import YOLO
from dataclasses import dataclass
from .mobilenet_v3_large import MobilenetV3Large
from supervision.draw.color import ColorPalette
from supervision.tools.detections import Detections, BoxAnnotator


@dataclass(frozen=True)
class BYTETrackerArgs:
    track_thresh: float = 0.25
    track_buffer: int = 30
    match_thresh: float = 0.8
    aspect_ratio_thresh: float = 3.0
    min_box_area: float = 1.0
    mot20: bool = False

class DetectObject():
    def __init__(self, yolo_path, mobilenet_path, LINE_START, LINE_END):
        self.model = YOLO(yolo_path)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.mobilenet = MobilenetV3Large.from_pretrained(mobilenet_path, device=device)

        # dict maping class_id to class_name
        self.CLASS_NAMES_DICT = self.model.model.names
        # class_ids of interest - here disk and tray

        # create instance of BoxAnnotator and LineCounterAnnotator
        self.box_annotator = BoxAnnotator(color=ColorPalette(), thickness=4, text_thickness=2, text_scale=1)

        ## dish_kakigori   - 0
        ## dish_emtry      - 1
        ## dish_not_emtry  - 2
        ## tray_kakigori   - 3
        ## tray_emtry      - 4
        ## tray_not_emtry  - 5
        self.CLASS_NAMES_DICT = ["dish_kakigori", "dish_emptry", "dish_not_emptry", 
                                "tray_kakigori", "tray_emptry", "tray_not_emptry"]
        
        # for display
        self.zone_polygon = np.array([
        [950, 60],  # top-left
        [1500, 220],  # top-right
        [1500, 310],  # bottom-right
        [920, 150]   # bottom-left
        ], dtype=np.int32)

        # for detect (try to detect objects leaving to serve)
        self.zone_polygon1 = np.array([
        [30, 60],  # top-left
        [580, 220],  # top-right
        [580, 290],  # bottom-right
        [0, 130]   # bottom-left
        ], dtype=np.int32)
        
        self.reset_params()

    def reset_params(self):

        # Track each object's zone status: {id: inside_zone_bool}
        self.object_status = {}
        self.entry_count = 0
        self.exit_count = 0
   
    def detect_frame(self, frame):
        if frame is None:
            raise Exception("frame is null")
       
        # Convert BGR (from OpenCV) to RGB (for model)
        # frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # get frame of dispatch area
        dis_area_x, dis_area_y = 920, 0
        x_size, y_size = 600, 290
        dis_frame = frame[dis_area_y:dis_area_y+y_size, dis_area_x:dis_area_x+x_size]
        

        # model prediction on single frame and conversion to supervision Detections
        # results = self.model(dis_frame)
        results = self.model.track(dis_frame, persist=True)

        # class
        class_id=results[0].boxes.cls.cpu().numpy().astype(int)
        new_class_id = []

        # box
        xyxy=results[0].boxes.xyxy.cpu().numpy()
        new_xyxy = []

        num_object = [0 for _ in range(len(self.CLASS_NAMES_DICT))]
        confidence = []

        for obj_id, box, conf in zip(results[0].boxes.id, xyxy, results[0].boxes.conf):
            obj_id = int(obj_id.item())  # convert to int
            # cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

            # Make sure they are integers
            x1b, y1b, x2b, y2b = map(int, box[:4])
            cx, cy = (x1b + x2b) // 2 , (y1b + y2b) // 2 

            # Check if center is inside polygon zone
            in_zone_now = cv2.pointPolygonTest(self.zone_polygon1, (cx, cy), False) >= 0
            in_zone_before = self.object_status.get(obj_id, None)

             # Entry
            if in_zone_now and in_zone_before == False:
                self.entry_count += 1
                self.object_status[obj_id] = True

            # Exit
            elif not in_zone_now and in_zone_before == True:
                self.exit_count += 1
                self.object_status[obj_id] = False

            # First time seeing the object
            elif in_zone_before is None:
                self.object_status[obj_id] = in_zone_now

            # Handle boundaries
            x1b, y1b = max(0, x1b), max(0, y1b)
            x2b, y2b = min(dis_frame.shape[1], x2b), min(dis_frame.shape[0], y2b)

            cropped = dis_frame[y1b:y2b, x1b:x2b]

            new_cls = self.mobilenet.classification(cropped).cpu().numpy()

            if in_zone_now:
                num_object[int(new_cls[0])] += 1

                # [x1, y1, x2, y2]
                new_xyxy.append([920 + box[0], 20 + box[1], 920 + box[2], 20 + box[3]])
                new_class_id.append(new_cls[0])
                confidence.append(conf)

        detections = Detections(
            xyxy =  np.array(new_xyxy),
            confidence=np.array(confidence),
            class_id= np.array(new_class_id))
        # print(f"cls: {results[0].boxes.cls}. box: {results[0].boxes.xyxy}")

        # format custom labels
        labels = [
            f"{self.CLASS_NAMES_DICT[class_id]} {confidence:0.2f}"
            for _, confidence, class_id, tracker_id
            in detections
        ]
 
        # Draw zone
        cv2.polylines(frame, [self.zone_polygon], isClosed=True, color=(255, 0, 0), thickness=2)
        # Show counts
        x = 350
        cv2.putText(frame, f"Number of entry objects: {self.entry_count}", (x, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 4)
        cv2.putText(frame, f"Number of exit objects: {self.exit_count}", (x, 190), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 4)
        cv2.putText(frame, f"Number of objects on the table:", (x, 230), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 4)
      
        y = 270
        for clssname, num in zip(self.CLASS_NAMES_DICT, num_object):  
            cv2.putText(frame, f"{clssname}: {num}", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 4)
            y += 40

        # annotate and display frame
        frame = self.box_annotator.annotate(frame=frame, detections=detections, labels=labels)
        return frame
    

if __name__ == "__main__":
    detector = DetectObject("/project/backend/models/trainedmodels/yoloDetect.pt")