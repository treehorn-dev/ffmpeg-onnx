FROM ubuntu:22.04
ARG TARGETARCH
ARG JELLYFIN_FFMPEG_VERSION=7.1.3-6

RUN if [ "$TARGETARCH" = "arm64" ]; then \
      UBUNTU_MIRROR="http://ports.ubuntu.com/ubuntu-ports"; \
    else \
      UBUNTU_MIRROR="http://archive.ubuntu.com/ubuntu"; \
    fi && \
    echo "deb [trusted=yes] ${UBUNTU_MIRROR} jammy main restricted universe multiverse" > /etc/apt/sources.list && \
    echo "deb [trusted=yes] ${UBUNTU_MIRROR} jammy-updates main restricted universe multiverse" >> /etc/apt/sources.list && \
    echo "deb [trusted=yes] ${UBUNTU_MIRROR} jammy-security main restricted universe multiverse" >> /etc/apt/sources.list && \
    apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 update && \
    apt-get install -y --fix-missing --no-install-recommends \
    ca-certificates wget python3 python3-pip \
    libgomp1 libopenblas0 libusb-1.0-0 && \
    rm -rf /var/lib/apt/lists/*

RUN wget -O /tmp/jellyfin-ffmpeg7.deb \
    "https://github.com/jellyfin/jellyfin-ffmpeg/releases/download/v${JELLYFIN_FFMPEG_VERSION}/jellyfin-ffmpeg7_${JELLYFIN_FFMPEG_VERSION}-jammy_${TARGETARCH}.deb" && \
    apt-get update && \
    apt-get install -y --fix-missing --no-install-recommends /tmp/jellyfin-ffmpeg7.deb && \
    rm -f /tmp/jellyfin-ffmpeg7.deb && \
    rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir numpy opencv-python-headless openvino

RUN ln -s /usr/lib/jellyfin-ffmpeg/ffmpeg /usr/local/bin/ffmpeg && \
    ln -s /usr/lib/jellyfin-ffmpeg/ffprobe /usr/local/bin/ffprobe

COPY process_nudenet.py /usr/local/bin/process_nudenet.py
COPY viz_nudenet.py /usr/local/bin/viz_nudenet.py
COPY ffmpeg_onnx_cli.py /usr/local/bin/ffmpeg-onnx
RUN chmod +x /usr/local/bin/ffmpeg-onnx

WORKDIR /work
ENTRYPOINT ["ffmpeg-onnx"]
