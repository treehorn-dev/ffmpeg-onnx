# ffmpeg-onnx

Docker image for running NudeNet inference over video and emitting JSONL detections, plus an optional visualization step.

The container exposes a small JSON-first CLI through `ffmpeg-onnx`:

- `ffmpeg-onnx process`: run inference and write a `.jsonl` file

## Build

```bash
docker build -t ffmpeg-onnx .
```

## Release-Backed Assets

The base `Dockerfile` keeps the original mounted-model workflow.

For CI or a bundled runtime image, fetch the model assets from a GitHub release into `models/` first:

```bash
./scripts/fetch-release-assets.sh nudenet-assets-v1
```

That uses:

```bash
gh release download nudenet-assets-v1 -R treehorn-dev/ffmpeg-onnx -D models -p nudenet.onnx -p labels.txt
```

Then build the base image and the baked-model variant:

```bash
docker build -t ffmpeg-onnx-base .
docker build -t ffmpeg-onnx:baked -f Dockerfile.baked .
```

The baked variant copies:
- `models/nudenet.onnx`
- `labels.txt` to `/models/labels.txt`

## What The Image Contains

- Jellyfin FFmpeg and FFprobe binaries from a pinned GitHub release package
- OpenVINO Python runtime
- Python CLI entrypoint: `ffmpeg-onnx`

The image does **not** bundle `nudenet.onnx`. Mount the model file when you run `process`.

## Quick Start

Run inference on a single video and write detections beside it:

```bash
docker run --rm \
  -v /absolute/path/to/videos:/work \
  -v /absolute/path/to/nudenet.onnx:/models/nudenet.onnx:ro \
  --user "$(id -u):$(id -g)" \
  ffmpeg-onnx process \
  --video /work/input.mp4 \
  --model /models/nudenet.onnx \
  --output /work/input.mp4.bbox.jsonl
```

The command returns a JSON envelope like:

```json
{
  "ok": true,
  "command": "ffmpeg-onnx process --video /work/input.mp4 --model /models/nudenet.onnx --output /work/input.mp4.bbox.jsonl",
  "result": {
    "output_file": "/work/input.mp4.bbox.jsonl",
    "status": "completed",
    "metrics": {
      "video_seconds": 137.8,
      "sampled_frames": 689,
      "elapsed_seconds": 14.993,
      "sampled_fps": 45.953,
      "realtime_factor": 9.191
    }
  },
  "next_actions": [
    {
      "command": "ffmpeg-onnx process --video /work/input.mp4 --model /models/nudenet.onnx --output /work/input.mp4.bbox.jsonl",
      "description": "Run the supported NudeNet processing path again"
    }
  ]
}
```

## Commands

Show the command tree:

```bash
docker run --rm ffmpeg-onnx
```

### `process`

Arguments:

- `--video`: input video path inside the container
- `--model`: ONNX model path inside the container
- `--fps`: sampling rate for inference, default `5.0`
- `--output`: JSONL output path, default `detections.jsonl`

Example:

```bash
docker run --rm \
  -v /absolute/path/to/videos:/work \
  -v /absolute/path/to/nudenet.onnx:/models/nudenet.onnx:ro \
  --user "$(id -u):$(id -g)" \
  ffmpeg-onnx process \
  --video /work/input.mp4 \
  --model /models/nudenet.onnx \
  --fps 5 \
  --output /work/input.mp4.bbox.jsonl
```

Notes:

- Video decoding and frame sampling are done through FFmpeg, not `cv2.VideoCapture`.
- The JSONL only contains frames with non-empty detections.
- The JSON envelope includes throughput metrics under `result.metrics`.

## Batch Processing

Process every `.mp4` in a directory:

```bash
for i in /absolute/path/to/videos/*.mp4; do
  base="$(basename "$i")"
  docker run --rm \
    -v /absolute/path/to/videos:/work \
    -v /absolute/path/to/nudenet.onnx:/models/nudenet.onnx:ro \
    --user "$(id -u):$(id -g)" \
    ffmpeg-onnx process \
    --video "/work/$base" \
    --model /models/nudenet.onnx \
    --output "/work/$base.bbox.jsonl"
done
```

Skip videos that already have an output file:

```bash
for i in /absolute/path/to/videos/*.mp4; do
  base="$(basename "$i")"
  out="/absolute/path/to/videos/$base.bbox.jsonl"
  [ -f "$out" ] && { echo "skip: $base"; continue; }

  docker run --rm \
    -v /absolute/path/to/videos:/work \
    -v /absolute/path/to/nudenet.onnx:/models/nudenet.onnx:ro \
    --user "$(id -u):$(id -g)" \
    ffmpeg-onnx process \
    --video "/work/$base" \
    --model /models/nudenet.onnx \
    --output "/work/$base.bbox.jsonl"
done
```

## JSONL Format

Each line contains one sampled frame with detections:

```json
{
  "timestamp": 0.2,
  "time_offset": "00:00:00.200",
  "millisecond": 200,
  "frame": 12,
  "detections": [
    {
      "label": "FACE_FEMALE",
      "confidence": 0.6436,
      "box": [0.4869, 0.2371, 0.5818, 0.4195]
    }
  ]
}
```

`box` is normalized as `[x1, y1, x2, y2]`.

## Troubleshooting

### `Could not open the file: "/nudenet.onnx"`

You did not mount the model into the container. Add:

```bash
-v /absolute/path/to/nudenet.onnx:/models/nudenet.onnx:ro
```

and then use:

```bash
--model /models/nudenet.onnx
```

### `FileNotFoundError` for the JSONL file during `viz`

Make sure the exact file passed to `--jsonl` exists in the mounted directory. `viz` does not generate detections; it only reads an existing `.jsonl`.

### Output video disappeared

You wrote it somewhere ephemeral like `/tmp` and used `--rm`. Write outputs you want to keep under the mounted `/work` directory.
