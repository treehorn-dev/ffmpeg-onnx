import cv2
import numpy as np
import json
import argparse
import subprocess
import time
from openvino.runtime import Core
from datetime import timedelta

LABELS = [
    "FEMALE_GENITALIA_COVERED",
    "FACE_FEMALE",
    "BUTTOCKS_EXPOSED",
    "FEMALE_BREAST_EXPOSED",
    "FEMALE_GENITALIA_EXPOSED",
    "MALE_BREAST_EXPOSED",
    "ANUS_EXPOSED",
    "FEET_EXPOSED",
    "BELLY_COVERED",
    "FEET_COVERED",
    "ARMPITS_COVERED",
    "ARMPITS_EXPOSED",
    "FACE_MALE",
    "BELLY_EXPOSED",
    "MALE_GENITALIA_EXPOSED",
    "ANUS_COVERED",
    "FEMALE_BREAST_COVERED",
    "BUTTOCKS_COVERED"
]

def format_timestamp(seconds):
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds_int = divmod(remainder, 60)
    milliseconds = int(td.microseconds / 1000)
    return f"{hours:02}:{minutes:02}:{seconds_int:02}.{milliseconds:03}"

def postprocess(result, model_w, model_h, conf_threshold=0.3):
    # result is raw YOLOv8 output: [1, 4 + num_classes, 8400]
    result = result[0]
    result = result.transpose() # [8400, 22]
    
    boxes = []
    scores = []
    class_ids = []
    
    for row in result:
        bbox = row[:4]
        class_scores = row[4:]
        class_id = np.argmax(class_scores)
        score = class_scores[class_id]
        
        if score > conf_threshold:
            boxes.append(bbox)
            scores.append(float(score))
            class_ids.append(int(class_id))
            
    if not boxes:
        return []
        
    boxes = np.array(boxes)
    # Convert from [x_center, y_center, w, h] to [x1, y1, x2, y2]
    x_center, y_center, w, h = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
    x1 = (x_center - w / 2) / model_w
    y1 = (y_center - h / 2) / model_h
    x2 = (x_center + w / 2) / model_w
    y2 = (y_center + h / 2) / model_h
    
    # NMS requires pixel coords, so we use normalized * 1000 for stability or just raw pixels
    indices = cv2.dnn.NMSBoxes(
        [ [float(x_center[i] - w[i]/2), float(y_center[i] - h[i]/2), float(w[i]), float(h[i])] for i in range(len(boxes)) ],
        scores, conf_threshold, 0.45
    )
    
    final_results = []
    if len(indices) > 0:
        for i in indices.flatten():
            final_results.append({
                "label": LABELS[class_ids[i]] if class_ids[i] < len(LABELS) else f"unknown_{class_ids[i]}",
                "confidence": round(float(scores[i]), 4),
                "box": [round(float(x1[i]), 4), round(float(y1[i]), 4), round(float(x2[i]), 4), round(float(y2[i]), 4)]
            })
            
    return final_results


def build_ffmpeg_decode_command(video_path, fps):
    return [
        "ffmpeg",
        "-v", "error",
        "-i", video_path,
        "-vf", f"fps={fps}",
        "-f", "rawvideo",
        "-pix_fmt", "bgr24",
        "pipe:1",
    ]


def probe_video_stream(video_path):
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,avg_frame_rate",
        "-of", "json",
        video_path,
    ]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    data = json.loads(result.stdout)
    stream = data["streams"][0]
    numerator, denominator = stream["avg_frame_rate"].split("/")
    fps = float(numerator) / float(denominator) if float(denominator) else 0.0
    return int(stream["width"]), int(stream["height"]), fps


def iter_sampled_frames(video_path, fps):
    width, height, source_fps = probe_video_stream(video_path)
    frame_bytes = width * height * 3
    cmd = build_ffmpeg_decode_command(video_path, fps)
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    sampled_index = 0
    try:
        while True:
            raw = process.stdout.read(frame_bytes)
            if len(raw) == 0:
                break
            if len(raw) != frame_bytes:
                raise RuntimeError("ffmpeg produced a partial video frame")

            frame = np.frombuffer(raw, dtype=np.uint8).reshape((height, width, 3))
            timestamp_sec = sampled_index / fps if fps > 0 else 0.0
            frame_number = int(round(timestamp_sec * source_fps)) if source_fps > 0 else sampled_index
            yield frame_number, timestamp_sec, frame
            sampled_index += 1
    finally:
        if process.stdout:
            process.stdout.close()
        stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
        if process.stderr:
            process.stderr.close()
        return_code = process.wait()
        if return_code != 0:
            raise RuntimeError(f"ffmpeg decode failed: {stderr.strip()}")


def build_processing_summary(video_seconds, sampled_frames, elapsed_seconds):
    sampled_fps = sampled_frames / elapsed_seconds if elapsed_seconds > 0 else 0.0
    realtime_factor = video_seconds / elapsed_seconds if elapsed_seconds > 0 else 0.0
    return {
        "video_seconds": round(float(video_seconds), 3),
        "sampled_frames": int(sampled_frames),
        "elapsed_seconds": round(float(elapsed_seconds), 3),
        "sampled_fps": round(float(sampled_fps), 3),
        "realtime_factor": round(float(realtime_factor), 3),
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--video", required=True)
    parser.add_argument("--fps", type=float, default=5.0)
    parser.add_argument("--output", default="detections.jsonl")
    args = parser.parse_args()

    ie = Core()
    model = ie.read_model(args.model)
    compiled_model = ie.compile_model(model, "CPU")
    input_layer = compiled_model.input(0)
    output_layer = compiled_model.output(0)
    
    _, _, h, w = input_layer.shape

    start_time = time.perf_counter()
    sampled_frames = 0
    max_timestamp_sec = 0.0

    with open(args.output, "w") as f:
        for frame_number, timestamp_sec, frame in iter_sampled_frames(args.video, args.fps):
            ms_offset = timestamp_sec * 1000.0
            sampled_frames += 1
            max_timestamp_sec = timestamp_sec

            input_img = cv2.resize(frame, (w, h))
            input_img = input_img.transpose(2, 0, 1)
            input_img = input_img.reshape(1, 3, h, w).astype(np.float32) / 255.0

            res = compiled_model([input_img])[output_layer]
            detections = postprocess(res, w, h)

            if detections:
                entry = {
                    "timestamp": timestamp_sec,
                    "time_offset": format_timestamp(timestamp_sec),
                    "millisecond": int(ms_offset),
                    "frame": frame_number,
                    "detections": detections
                }
                f.write(json.dumps(entry) + "\n")

    elapsed_seconds = time.perf_counter() - start_time
    video_seconds = max_timestamp_sec + (1.0 / args.fps if sampled_frames > 0 and args.fps > 0 else 0.0)
    print(json.dumps(build_processing_summary(video_seconds, sampled_frames, elapsed_seconds)))

if __name__ == "__main__":
    main()
