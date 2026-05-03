from pathlib import Path
import sys
import types

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

cv2_stub = types.SimpleNamespace(dnn=types.SimpleNamespace(NMSBoxes=lambda *args, **kwargs: []))
openvino_runtime_stub = types.SimpleNamespace(Core=object)
numpy_stub = types.SimpleNamespace()
sys.modules.setdefault("cv2", cv2_stub)
sys.modules.setdefault("numpy", numpy_stub)
sys.modules.setdefault("openvino", types.SimpleNamespace(runtime=openvino_runtime_stub))
sys.modules.setdefault("openvino.runtime", openvino_runtime_stub)

import process_nudenet


def test_build_ffmpeg_decode_command_uses_ffmpeg_sampling():
    cmd = process_nudenet.build_ffmpeg_decode_command(
        video_path="/work/input.mp4",
        fps=5.0,
    )

    assert cmd[:2] == ["ffmpeg", "-v"]
    assert "/work/input.mp4" in cmd
    assert "fps=5.0" in cmd
    assert "rawvideo" in cmd
    assert "pipe:1" in cmd


def test_build_processing_summary_reports_throughput():
    summary = process_nudenet.build_processing_summary(
        video_seconds=10.0,
        sampled_frames=50,
        elapsed_seconds=2.0,
    )

    assert summary == {
        "video_seconds": 10.0,
        "sampled_frames": 50,
        "elapsed_seconds": 2.0,
        "sampled_fps": 25.0,
        "realtime_factor": 5.0,
    }
