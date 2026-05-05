ARG FFMPEG_ONNX_BOOTSTRAP_IMAGE=ghcr.io/treehorn-dev/ffmpeg-onnx:baked-latest
FROM ${FFMPEG_ONNX_BOOTSTRAP_IMAGE}
ARG TARGETARCH
ARG JELLYFIN_FFMPEG_VERSION=7.1.3-6

RUN rm -f /models/nudenet.onnx /models/labels.txt

RUN pip3 install --no-cache-dir --upgrade numpy opencv-python-headless openvino

RUN ln -sf /usr/lib/jellyfin-ffmpeg/ffmpeg /usr/local/bin/ffmpeg && \
    ln -sf /usr/lib/jellyfin-ffmpeg/ffprobe /usr/local/bin/ffprobe

COPY process_nudenet.py /usr/local/bin/process_nudenet.py
COPY viz_nudenet.py /usr/local/bin/viz_nudenet.py
COPY ffmpeg_onnx_cli.py /usr/local/bin/ffmpeg-onnx
RUN chmod +x /usr/local/bin/ffmpeg-onnx

WORKDIR /work
ENTRYPOINT ["ffmpeg-onnx"]
