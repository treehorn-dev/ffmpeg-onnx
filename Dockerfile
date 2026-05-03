# Stage 1: Build FFmpeg with Libtorch and OpenVINO
FROM ubuntu:22.04 AS build

# Install dependencies
RUN echo "deb [trusted=yes] http://ports.ubuntu.com/ubuntu-ports jammy main restricted universe multiverse" > /etc/apt/sources.list && \
    echo "deb [trusted=yes] http://ports.ubuntu.com/ubuntu-ports jammy-updates main restricted universe multiverse" >> /etc/apt/sources.list && \
    echo "deb [trusted=yes] http://ports.ubuntu.com/ubuntu-ports jammy-security main restricted universe multiverse" >> /etc/apt/sources.list && \
    apt-get update && apt-get install -y \
    wget tar cmake git build-essential \
    pkg-config libssl-dev libfreetype6-dev \
    unzip libopenblas-dev libusb-1.0-0-dev

# Install PyTorch C++ (Libtorch) CPU version for aarch64 (Linux Arm64)
RUN mkdir -p /usr/local/libtorch \
    && wget -O libtorch.tar.gz https://github.com/second-state/libtorch-releases/releases/download/v2.4.0/libtorch-cxx11-abi-aarch64-2.4.0.tar.gz \
    && tar -xzf libtorch.tar.gz -C /usr/local/libtorch --strip-components=1 \
    && rm libtorch.tar.gz

# Install OpenVINO for aarch64 (Linux Arm64)
RUN mkdir -p /usr/local/openvino \
    && wget -O openvino.tgz https://storage.openvinotoolkit.org/repositories/openvino/packages/2025.4/linux/openvino_toolkit_ubuntu22_2025.4.0.20398.8fdad55727d_arm64.tgz \
    && tar -xzf openvino.tgz -C /usr/local/openvino --strip-components=1 \
    && rm openvino.tgz

# Manually create openvino.pc
RUN mkdir -p /usr/local/openvino/pkgconfig && \
    echo "prefix=/usr/local/openvino" > /usr/local/openvino/pkgconfig/openvino.pc && \
    echo "exec_prefix=\${prefix}" >> /usr/local/openvino/pkgconfig/openvino.pc && \
    echo "libdir=\${prefix}/runtime/lib/aarch64" >> /usr/local/openvino/pkgconfig/openvino.pc && \
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
RUN echo "deb [trusted=yes] http://ports.ubuntu.com/ubuntu-ports jammy main restricted universe multiverse" > /etc/apt/sources.list && \
    echo "deb [trusted=yes] http://ports.ubuntu.com/ubuntu-ports jammy-updates main restricted universe multiverse" >> /etc/apt/sources.list && \
    echo "deb [trusted=yes] http://ports.ubuntu.com/ubuntu-ports jammy-security main restricted universe multiverse" >> /etc/apt/sources.list && \
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
COPY nn.py /usr/local/bin/nn
RUN chmod +x /usr/local/bin/nn

# Ensure loader finds libraries
ENV LD_LIBRARY_PATH=/usr/local/libtorch/lib:/usr/local/openvino/runtime/lib/aarch64:/usr/local/openvino/runtime/3rdparty/tbb/lib
ENV PYTHONPATH=/usr/local/openvino/python
ENV PATH="/usr/local/bin:${PATH}"

WORKDIR /work
ENTRYPOINT ["nn"]
