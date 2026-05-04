from __future__ import annotations

import json


def parse_process_summary(stdout: str):
    stdout = (stdout or "").strip()
    if not stdout:
        return {}
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {"raw_summary": stdout}


def build_process_result(output_file: str, summary=None):
    result = {
        "output_file": output_file,
        "status": "completed",
    }
    if summary:
        result["metrics"] = summary
    return result
