import cv2
import numpy as np
import json
import argparse
import os
import subprocess

COLORS = [
    (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (0, 255, 255), (255, 0, 255),
    (128, 0, 0), (0, 128, 0), (0, 0, 128), (128, 128, 0), (0, 128, 128), (128, 0, 128),
    (64, 0, 0), (0, 64, 0), (0, 0, 64), (64, 64, 0), (0, 64, 64), (64, 0, 64)
]

LABELS = [
    "FEMALE_GENITALIA_COVERED", "FACE_FEMALE", "BUTTOCKS_EXPOSED", "FEMALE_BREAST_EXPOSED",
    "FEMALE_GENITALIA_EXPOSED", "MALE_BREAST_EXPOSED", "ANUS_EXPOSED", "FEET_EXPOSED",
    "BELLY_COVERED", "FEET_COVERED", "ARMPITS_COVERED", "ARMPITS_EXPOSED", "FACE_MALE",
    "BELLY_EXPOSED", "MALE_GENITALIA_EXPOSED", "ANUS_COVERED", "FEMALE_BREAST_COVERED",
    "BUTTOCKS_COVERED"
]

LABEL_TO_COLOR = {label: COLORS[i % len(COLORS)] for i, label in enumerate(LABELS)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--jsonl", required=True)
    parser.add_argument("--output", default="viz.mp4")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    # Load detections
    detections_map = {}
    with open(args.jsonl, 'r') as f:
        for i, line in enumerate(f):
            if i >= args.limit and args.limit > 0:
                break
            data = json.loads(line)
            detections_map[data['frame']] = data['detections']

    cap = cv2.VideoCapture(args.video)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    os.makedirs("frames", exist_ok=True)
    
    frame_count = 0
    frames_processed = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret or (args.limit > 0 and frames_processed >= args.limit):
            break
            
        if frame_count in detections_map:
            overlay = frame.copy()
            for det in detections_map[frame_count]:
                label = det['label']
                conf = det['confidence']
                box = det['box'] # normalized [x1, y1, x2, y2]
                
                x1, y1, x2, y2 = int(box[0]*width), int(box[1]*height), int(box[2]*width), int(box[3]*height)
                color = LABEL_TO_COLOR.get(label, (255, 255, 255))
                
                # Draw translucent box
                cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
                alpha = conf * 0.6 # Max alpha 0.6
                cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
                
                # Draw border and label
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, f"{label} {conf:.2f}", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            frame_path = f"frames/frame_{frame_count:06d}.png"
            cv2.imwrite(frame_path, frame)
            frames_processed += 1
            
        frame_count += 1
        
    cap.release()
    
    # Composite into mp4
    print(f"Compositing {frames_processed} frames into {args.output}...")
    cmd = [
        "ffmpeg", "-y", "-framerate", "5", 
        "-pattern_type", "glob", "-i", "frames/*.png",
        "-c:v", "mpeg4", "-q:v", "5",
        args.output
    ]
    subprocess.run(cmd, check=True)
    print("Done.")

if __name__ == "__main__":
    main()
