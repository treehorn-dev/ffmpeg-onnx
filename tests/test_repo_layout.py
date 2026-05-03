from pathlib import Path


def test_repo_has_clean_minimal_layout() -> None:
    assert Path("Dockerfile").exists()
    assert Path("README.md").exists()
    assert Path("nn.py").exists()
    assert Path("process_nudenet.py").exists()
    assert Path("viz_nudenet.py").exists()
    assert Path("ffmpeg-8.1").is_dir()
    assert Path("tests/test_process_nudenet.py").exists()


def test_repo_has_gitignore_for_local_artifacts() -> None:
    text = Path(".gitignore").read_text()

    assert "frames/" in text
    assert "*.mp4" in text
    assert "*.jsonl" in text
    assert "*.onnx" in text


def test_repo_has_pytest_harness() -> None:
    text = Path("pyproject.toml").read_text()

    assert "[project]" in text
    assert "pytest" in text
    assert "[tool.pytest.ini_options]" in text
