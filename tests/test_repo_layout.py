from pathlib import Path


def test_repo_has_clean_minimal_layout() -> None:
    assert Path("Dockerfile").exists()
    assert Path("Dockerfile.baked").exists()
    assert Path("README.md").exists()
    assert Path("labels.txt").exists()
    assert Path("models/.gitkeep").exists()
    assert Path("ffmpeg_onnx_cli.py").exists()
    assert Path("process_nudenet.py").exists()
    assert Path("viz_nudenet.py").exists()
    assert Path("ffmpeg-8.1").is_dir()
    assert Path("scripts/fetch-release-assets.sh").exists()
    assert Path("tests/test_process_nudenet.py").exists()


def test_repo_has_gitignore_for_local_artifacts() -> None:
    text = Path(".gitignore").read_text()

    assert "frames/" in text
    assert "*.mp4" in text
    assert "*.jsonl" in text
    assert "*.onnx" in text
    assert "models/*" in text
    assert "!models/.gitkeep" in text


def test_repo_has_pytest_harness() -> None:
    text = Path("pyproject.toml").read_text()

    assert "[project]" in text
    assert "pytest" in text
    assert "[tool.pytest.ini_options]" in text


def test_main_dockerfile_installs_pinned_jellyfin_ffmpeg_packages() -> None:
    text = Path("Dockerfile").read_text()

    assert "ARG FFMPEG_ONNX_BOOTSTRAP_IMAGE=ghcr.io/treehorn-dev/ffmpeg-onnx:baked-latest" in text
    assert "FROM ${FFMPEG_ONNX_BOOTSTRAP_IMAGE}" in text
    assert "ARG TARGETARCH" in text
    assert "JELLYFIN_FFMPEG_VERSION" in text
    assert "rm -f /models/nudenet.onnx /models/labels.txt" in text
    assert "pip3 install --no-cache-dir --upgrade numpy opencv-python-headless openvino" in text
    assert "ln -sf /usr/lib/jellyfin-ffmpeg/ffmpeg /usr/local/bin/ffmpeg" in text
    assert "ln -sf /usr/lib/jellyfin-ffmpeg/ffprobe /usr/local/bin/ffprobe" in text
    assert "./configure" not in text
    assert "make -j$(nproc) install" not in text


def test_baked_model_dockerfile_copies_release_backed_assets() -> None:
    text = Path("Dockerfile.baked").read_text()

    assert "ARG FFMPEG_ONNX_BASE_IMAGE=ffmpeg-onnx-base" in text
    assert "FROM ${FFMPEG_ONNX_BASE_IMAGE}" in text
    assert "COPY models/nudenet.onnx /models/nudenet.onnx" in text
    assert "COPY labels.txt /models/labels.txt" in text


def test_readme_documents_release_asset_flow() -> None:
    text = Path("README.md").read_text()

    assert "gh release download" in text
    assert "Dockerfile.baked" in text
    assert "models/nudenet.onnx" in text
