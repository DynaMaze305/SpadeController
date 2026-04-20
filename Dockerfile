FROM --platform=arm64 dtcooper/raspberrypi-os:python3.13

ENV PYTHONUNBUFFERED=1

RUN apt update && \
    apt install -y --no-install-recommends \
        python3-venv \
        python3-smbus \
        python3-serial \
        python3-pip \
        libcap-dev \
        python3-picamera2 \
        python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create a venv to install dependencies
# with system python but not in system packages
RUN /usr/bin/python3 -m venv --system-site-packages /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install -r requirements.txt

CMD ["python", "-m", "agent"]