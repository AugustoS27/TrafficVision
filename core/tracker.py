import supervision as sv
import numpy as np

class Tracker:
    def __init__(self):
        self.tracker = sv.ByteTrack(
            track_activation_threshold=0.25,
            lost_track_buffer=30,
            minimum_matching_threshold=0.8,
            frame_rate=30
        )
        
        self.box_annotator = sv.BoxAnnotator(
            thickness=2
        )
        self.label_annotator = sv.LabelAnnotator(
            text_scale=0.5,
            text_thickness=1,
            text_padding=10
        )
        
        self.CLASS_NAMES_DICT = {
            2: "Auto",
            3: "Moto",   # No son detectadas por el modelo
            5: "Camion", # No son detectadas por el modelo
            7: "Camion"
        }

    def update(self, detections):
        tracked_detections = self.tracker.update_with_detections(detections)
        return tracked_detections

    def draw(self, frame, tracked_detections):
        if tracked_detections.tracker_id is None or len(tracked_detections.tracker_id) == 0:
            return frame

        annotated_frame = self.box_annotator.annotate(
            scene=frame.copy(),
            detections=tracked_detections
        )
        
        labels = []
        for tracker_id, class_id in zip(tracked_detections.tracker_id, tracked_detections.class_id):
            class_name = self.CLASS_NAMES_DICT.get(class_id, "Otro")
            labels.append(f"#{tracker_id} {class_name}")
        
        annotated_frame = self.label_annotator.annotate(
            scene=annotated_frame,
            detections=tracked_detections,
            labels=labels
        )
        
        return annotated_frame