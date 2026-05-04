from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

VERSION = "0.1.0"
SUPPORTED_MODELS = {"nudenet"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    subparsers = parser.add_subparsers(dest="command")

    process_parser = subparsers.add_parser("process", add_help=False)
    process_parser.add_argument("--model", default="nudenet")
    process_parser.add_argument("--input", required=True)
    process_parser.add_argument("--output-jsonl")
    process_parser.add_argument("--visualize")

    return parser


def main(argv: list[str] | None = None, executable: str = "ffmpeg-onnx") -> int:
    argv = list(argv or [])
    raw = command_raw(executable, argv)
    if not argv:
        emit(root_payload(raw, executable))
        return 0

    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        emit(error_response(raw, {"path": argv[:1], "options": {}, "flags": {}}, "INVALID_ARGUMENTS", "Invalid command arguments.", "Run the root command to inspect supported ffmpeg-onnx commands.", [{"command": executable, "description": "Show the root command tree."}], executable))
        return 2

    if args.command == "process":
        parsed = {
            "path": ["process"],
            "options": {
                "model": args.model,
                "input": args.input,
                "output_jsonl": args.output_jsonl,
                "visualize": args.visualize,
            },
            "flags": {},
        }
        if args.model not in SUPPORTED_MODELS:
            emit(error_response(raw, parsed, "UNSUPPORTED_MODEL", f"Unsupported model: {args.model}", "Use --model nudenet. That is the only supported model right now.", [{"command": f"{executable} process --model nudenet --input {args.input}", "description": "Run the supported NudeNet processing path."}], executable))
            return 1
        result = run_process_command(parsed)
        emit(success_response(raw, parsed, result, [{"command": f"{executable} process --model nudenet --input {args.input}", "description": "Re-run the supported NudeNet processing path."}], executable))
        return 0

    emit(root_payload(raw, executable))
    return 0


def main_entry() -> None:
    raise SystemExit(main(sys.argv[1:], executable="ffmpeg-onnx"))


def nn_entry() -> None:
    raise SystemExit(main(sys.argv[1:], executable="nn"))


def root_payload(raw: str, executable: str) -> dict[str, Any]:
    return success_response(raw, {"path": [], "options": {}, "flags": {}}, {
        "description": "ffmpeg-onnx CLI",
        "commands": [
            {
                "name": "process",
                "description": "Run the supported ONNX video processing path for a baked model.",
                "usage": f"{executable} process --model nudenet --input <video>",
            }
        ],
    }, [{"command": f"{executable} process --model nudenet --input /path/to/video.mp4", "description": "Process one video with the supported NudeNet model."}], executable)


def run_process_command(parsed: dict[str, Any]) -> dict[str, Any]:
    input_path = Path(parsed["options"]["input"])
    if not input_path.exists():
        raise FileNotFoundError(str(input_path))
    return {
        "model": parsed["options"]["model"],
        "input": str(input_path),
        "status": "ready",
        "note": "Execution wiring is preserved through the existing ffmpeg-onnx scripts.",
    }


def success_response(raw: str, parsed: dict[str, Any], result: dict[str, Any], next_actions: list[dict[str, str]], executable: str) -> dict[str, Any]:
    return {
        "ok": True,
        "command": {
            "raw": raw,
            "parsed": parsed,
            "resolved": {
                "executable": executable,
                "cwd": os.getcwd(),
                "version": VERSION,
            },
        },
        "result": result,
        "next_actions": next_actions,
    }


def error_response(raw: str, parsed: dict[str, Any], code: str, message: str, fix: str, next_actions: list[dict[str, str]], executable: str) -> dict[str, Any]:
    return {
        "ok": False,
        "command": {
            "raw": raw,
            "parsed": parsed,
            "resolved": {
                "executable": executable,
                "cwd": os.getcwd(),
                "version": VERSION,
            },
        },
        "result": {},
        "next_actions": next_actions,
        "error": {"message": message, "code": code},
        "fix": fix,
    }


def command_raw(executable: str, argv: list[str]) -> str:
    return " ".join([executable, *argv]).strip()


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))
