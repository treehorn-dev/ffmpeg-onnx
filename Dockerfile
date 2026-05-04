# Stage 1: Build FFmpeg with Libtorch and OpenVINO
FROM ubuntu:22.04 AS build
ARG TARGETARCH

# Install dependencies
RUN if [ "$TARGETARCH" = "arm64" ]; then \
      UBUNTU_MIRROR="http://ports.ubuntu.com/ubuntu-ports"; \
    else \
      UBUNTU_MIRROR="http://archive.ubuntu.com/ubuntu"; \
    fi && \
    echo "deb [trusted=yes] ${UBUNTU_MIRROR} jammy main restricted universe multiverse" > /etc/apt/sources.list && \
    echo "deb [trusted=yes] ${UBUNTU_MIRROR} jammy-updates main restricted universe multiverse" >> /etc/apt/sources.list && \
    echo "deb [trusted=yes] ${UBUNTU_MIRROR} jammy-security main restricted universe multiverse" >> /etc/apt/sources.list && \
    apt-get update && apt-get install -y \
    wget tar cmake git build-essential \
    pkg-config libssl-dev libfreetype6-dev \
    unzip libopenblas-dev libusb-1.0-0-dev

# Install PyTorch C++ (Libtorch) CPU version for the target architecture.
RUN mkdir -p /usr/local/libtorch \
    && if [ "$TARGETARCH" = "arm64" ]; then \
         LIBTORCH_ARCH="aarch64"; \
       else \
         LIBTORCH_ARCH="x86_64"; \
       fi \
    && wget -O libtorch.tar.gz "https://github.com/second-state/libtorch-releases/releases/download/v2.4.0/libtorch-cxx11-abi-${LIBTORCH_ARCH}-2.4.0.tar.gz" \
    && tar -xzf libtorch.tar.gz -C /usr/local/libtorch --strip-components=1 \
    && rm libtorch.tar.gz

# Install OpenVINO for the target architecture.
RUN mkdir -p /usr/local/openvino \
    && if [ "$TARGETARCH" = "arm64" ]; then \
         OPENVINO_ARCHIVE="openvino_toolkit_ubuntu22_2025.4.0.20398.8fdad55727d_arm64.tgz"; \
       else \
         OPENVINO_ARCHIVE="openvino_toolkit_ubuntu22_2025.4.0.20398.8fdad55727d_x86_64.tgz"; \
       fi \
    && wget -O openvino.tgz "https://storage.openvinotoolkit.org/repositories/openvino/packages/2025.4/linux/${OPENVINO_ARCHIVE}" \
    && tar -xzf openvino.tgz -C /usr/local/openvino --strip-components=1 \
    && rm openvino.tgz

# Manually create openvino.pc
RUN mkdir -p /usr/local/openvino/pkgconfig && \
    if [ "$TARGETARCH" = "arm64" ]; then \
      OPENVINO_LIBDIR="aarch64"; \
    else \
      OPENVINO_LIBDIR="intel64"; \
    fi && \
    echo "prefix=/usr/local/openvino" > /usr/local/openvino/pkgconfig/openvino.pc && \
    echo "exec_prefix=\${prefix}" >> /usr/local/openvino/pkgconfig/openvino.pc && \
    echo "libdir=\${prefix}/runtime/lib/${OPENVINO_LIBDIR}" >> /usr/local/openvino/pkgconfig/openvino.pc && \
    echo "tbbdir=\${prefix}/runtime/3rdparty/tbb/lib" >> /usr/local/openvino/pkgconfig/openvino.pc && \
    echo "includedir=\${prefix}/runtime/include" >> /usr/local/openvino/pkgconfig/openvino.pc && \
    echo "" >> /usr/local/openvino/pkgconfig/openvino.pc && \
    echo "Name: openvino" >> /usr/local/openvino/pkgconfig/openvino.pc && \
    echo "Description: Intel(R) Distribution of OpenVINO(TM) toolkit" >> /usr/local/openvino/pkgconfig/openvino.pc && \
    echo "Version: 2025.4.0" >> /usr/local/openvino/pkgconfig/openvino.pc && \
    echo "Libs: -L\${libdir} -L\${tbbdir} -lopenvino -lopenvino_c -ltbb" >> /usr/local/openvino/pkgconfig/openvino.pc && \
    echo "Cflags: -I\${includedir}" >> /usr/local/openvino/pkgconfig/openvino.pc

ENV PKG_CONFIG_PATH=/usr/local/openvino/pkgconfig

# Build FFmpeg from local source
WORKDIR /ffmpeg_sources
COPY ffmpeg-8.1 ffmpeg-8.1
WORKDIR /ffmpeg_sources/ffmpeg-8.1

RUN ./configure \
    --prefix="/ffmpeg_build" \
    --pkg-config-flags="--static" \
    --disable-cuda \
    --disable-cuvid \
    --disable-nvenc \
    --enable-libtorch \
    --enable-libopenvino \
    --cxx="g++" \
    --extra-cflags="-I/usr/local/libtorch/include -I/usr/local/libtorch/include/torch/csrc/api/include" \
    --extra-cxxflags="-std=c++17 -I/usr/local/libtorch/include -I/usr/local/libtorch/include/torch/csrc/api/include" \
    --extra-ldflags="-L/usr/local/libtorch/lib" \
    --bindir="/bin" \
    && make -j$(nproc) install

# Stage 2: Final Image
FROM ubuntu:22.04
ARG TARGETARCH
RUN if [ "$TARGETARCH" = "arm64" ]; then \
      UBUNTU_MIRROR="http://ports.ubuntu.com/ubuntu-ports"; \
    else \
      UBUNTU_MIRROR="http://archive.ubuntu.com/ubuntu"; \
    fi && \
    echo "deb [trusted=yes] ${UBUNTU_MIRROR} jammy main restricted universe multiverse" > /etc/apt/sources.list && \
    echo "deb [trusted=yes] ${UBUNTU_MIRROR} jammy-updates main restricted universe multiverse" >> /etc/apt/sources.list && \
    echo "deb [trusted=yes] ${UBUNTU_MIRROR} jammy-security main restricted universe multiverse" >> /etc/apt/sources.list && \
    apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 libopenblas0 libusb-1.0-0 \
    python3 python3-pip \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir opencv-python-headless numpy

COPY --from=build /bin/ffmpeg /usr/local/bin/ffmpeg
COPY --from=build /bin/ffprobe /usr/local/bin/ffprobe
COPY --from=build /usr/local/libtorch /usr/local/libtorch
COPY --from=build /usr/local/openvino /usr/local/openvino

COPY process_nudenet.py /usr/local/bin/process_nudenet.py
COPY viz_nudenet.py /usr/local/bin/viz_nudenet.py
COPY ffmpeg_onnx_cli.py /usr/local/bin/ffmpeg-onnx
RUN chmod +x /usr/local/bin/ffmpeg-onnx
RUN if [ "$TARGETARCH" = "arm64" ]; then \
      ln -s /usr/local/openvino/runtime/lib/aarch64 /usr/local/openvino/runtime/lib/current; \
    else \
      ln -s /usr/local/openvino/runtime/lib/intel64 /usr/local/openvino/runtime/lib/current; \
    fi

# Ensure loader finds libraries
ENV LD_LIBRARY_PATH=/usr/local/libtorch/lib:/usr/local/openvino/runtime/lib/current:/usr/local/openvino/runtime/3rdparty/tbb/lib
ENV PYTHONPATH=/usr/local/openvino/python
ENV PATH="/usr/local/bin:${PATH}"

WORKDIR /work
ENTRYPOINT ["ffmpeg-onnx"]
