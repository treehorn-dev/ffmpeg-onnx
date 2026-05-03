from pathlib import Path
import sys
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import nn


def test_build_process_result_includes_perf_summary():
    summary = {
        "video_seconds": 10.0,
        "sampled_frames": 50,
        "elapsed_seconds": 2.0,
        "sampled_fps": 25.0,
        "realtime_factor": 5.0,
    }

    result = nn.build_process_result("/work/out.jsonl", summary)

    assert result["output_file"] == "/work/out.jsonl"
    assert result["status"] == "completed"
    assert result["metrics"] == summary


def test_parse_process_summary_reads_json_stdout():
    completed_stdout = json.dumps({"elapsed_seconds": 1.5, "sampled_frames": 7})

    summary = nn.parse_process_summary(completed_stdout)

    assert summary == {"elapsed_seconds": 1.5, "sampled_frames": 7}
