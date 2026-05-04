import json

import ffmpeg_onnx_cli


def test_root_command_returns_command_tree(capsys):
    exit_code = ffmpeg_onnx_cli.main([])
    assert exit_code == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["command"]["parsed"]["path"] == []
    assert payload["result"]["description"] == "ffmpeg-onnx CLI"
    assert any(command["name"] == "process" for command in payload["result"]["commands"])


def test_process_command_requires_supported_model(monkeypatch, capsys, tmp_path):
    video_path = tmp_path / "clip.mp4"
    video_path.write_bytes(b"fake")

    monkeypatch.setattr(ffmpeg_onnx_cli, "run_process_command", lambda parsed: {"model": "nudenet", "input": str(video_path), "status": "ok"})

    exit_code = ffmpeg_onnx_cli.main(["process", "--model", "nudenet", "--input", str(video_path)])
    assert exit_code == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["command"]["parsed"]["options"]["model"] == "nudenet"
    assert payload["result"]["model"] == "nudenet"


def test_process_command_rejects_unsupported_model(capsys, tmp_path):
    video_path = tmp_path / "clip.mp4"
    video_path.write_bytes(b"fake")

    exit_code = ffmpeg_onnx_cli.main(["process", "--model", "othernet", "--input", str(video_path)])
    assert exit_code == 1

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "UNSUPPORTED_MODEL"
    assert payload["command"]["parsed"]["options"]["model"] == "othernet"
    assert payload["fix"]


def test_nn_alias_uses_same_contract(capsys):
    exit_code = ffmpeg_onnx_cli.main([], executable="nn")
    assert exit_code == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["command"]["raw"] == "nn"
    assert payload["command"]["resolved"]["executable"] == "nn"
