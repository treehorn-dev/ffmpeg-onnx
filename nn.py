#!/usr/bin/env python3
import sys
import json
import subprocess
import argparse
import os

def parse_process_summary(stdout):
    stdout = (stdout or "").strip()
    if not stdout:
        return {}
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {"raw_summary": stdout}


def build_process_result(output_file, summary=None):
    result = {
        "output_file": output_file,
        "status": "completed"
    }
    if summary:
        result["metrics"] = summary
    return result


def output_json(ok, command, result=None, error=None, fix=None, next_actions=None):
    envelope = {
        "ok": ok,
        "command": command,
        "result": result or {},
        "next_actions": next_actions or []
    }
    if error:
        envelope["error"] = error
    if fix:
        envelope["fix"] = fix
    print(json.dumps(envelope, indent=2))
    sys.exit(0 if ok else 1)

def run_process(args):
    cmd = [
        "python3", "/usr/local/bin/process_nudenet.py",
        "--model", args.model,
        "--video", args.video,
        "--fps", str(args.fps),
        "--output", args.output
    ]
    try:
        completed = subprocess.run(cmd, check=True, capture_output=True, text=True)
        summary = parse_process_summary(completed.stdout)
        result = build_process_result(args.output, summary)
        next_actions = [
            {
                "command": f"nn viz --video {args.video} --jsonl {args.output}",
                "description": "Visualize detections on the video"
            }
        ]
        output_json(True, f"nn process {' '.join(sys.argv[2:])}", result, next_actions=next_actions)
    except subprocess.CalledProcessError as e:
        output_json(False, f"nn process {' '.join(sys.argv[2:])}", 
                    error={"message": e.stderr or str(e), "code": "PROCESS_FAILED"},
                    fix="Check model and video paths and ensure OpenVINO dependencies are met.")

def run_viz(args):
    cmd = [
        "python3", "/usr/local/bin/viz_nudenet.py",
        "--video", args.video,
        "--jsonl", args.jsonl,
        "--output", args.output,
        "--limit", str(args.limit)
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        result = {
            "output_file": args.output,
            "status": "completed"
        }
        output_json(True, f"nn viz {' '.join(sys.argv[2:])}", result)
    except subprocess.CalledProcessError as e:
        output_json(False, f"nn viz {' '.join(sys.argv[2:])}", 
                    error={"message": e.stderr or str(e), "code": "VIZ_FAILED"},
                    fix="Ensure FFmpeg is installed and the jsonl file exists.")

def main():
    if len(sys.argv) == 1:
        # Self-documenting command tree
        result = {
            "description": "NudeNet CLI — Video processing and visualization",
            "commands": [
                { "name": "process", "description": "Run NudeNet inference on video", "usage": "nn process --video <file> --model <model> [--fps 5] [--output detections.jsonl]" },
                { "name": "viz", "description": "Visualize detections on video", "usage": "nn viz --video <file> --jsonl <file> [--output viz.mp4] [--limit 100]" }
            ]
        }
        next_actions = [
            { "command": "nn process --help", "description": "See process command options" },
            { "command": "nn viz --help", "description": "See viz command options" }
        ]
        output_json(True, "nn", result, next_actions=next_actions)

    parser = argparse.ArgumentParser(prog="nn", add_help=False)
    subparsers = parser.add_subparsers(dest="command")

    # Process command
    proc_parser = subparsers.add_parser("process", add_help=False)
    proc_parser.add_argument("--video", required=True)
    proc_parser.add_argument("--model", required=True)
    proc_parser.add_argument("--fps", type=float, default=5.0)
    proc_parser.add_argument("--output", default="detections.jsonl")

    # Viz command
    viz_parser = subparsers.add_parser("viz", add_help=False)
    viz_parser.add_argument("--video", required=True)
    viz_parser.add_argument("--jsonl", required=True)
    viz_parser.add_argument("--output", default="viz.mp4")
    viz_parser.add_argument("--limit", type=int, default=100)

    if sys.argv[1] == "process":
        args, _ = proc_parser.parse_known_args(sys.argv[2:])
        run_process(args)
    elif sys.argv[1] == "viz":
        args, _ = viz_parser.parse_known_args(sys.argv[2:])
        run_viz(args)
    else:
        output_json(False, f"nn {sys.argv[1]}", error={"message": "Unknown command", "code": "UNKNOWN_COMMAND"})

if __name__ == "__main__":
    main()
