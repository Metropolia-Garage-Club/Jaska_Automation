# Development Environment - Usage Guide

## Overview
This guide covers how to use the ZED SDK Python API in docker on the Jaska robot. The environment is based on the camera Docker image with ZED SDK 5.1 and Python 3.11 in a conda environment.

## Prerequisites
- Jetson device (ZED Box) with NVIDIA runtime
- ZED X camera connected via GMSL
- Docker with NVIDIA container runtime installed

## Quick Start

### 1. Build Docker Image

```bash
cd samuli_dev
docker build -t samuli-dev:latest .
```

### 2. Run Docker Container (GMSL Camera Access)

```bash
xhost +
docker run -it --rm --name jaska \
  --gpus all \
  --runtime=nvidia \
  --privileged  \
  --network=host \
  --ipc=host \
  --pid=host \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -v /dev:/dev \
  -v /tmp:/tmp \
  -v /home/user/.Xauthority:/root/.Xauthority:rw \
  -v /tmp/argus_socket:/tmp/argus_socket \
  -v /var/nvidia/nvcam/settings/:/var/nvidia/nvcam/settings/ \
  -v /etc/systemd/system:/etc/systemd/system \
  -v /etc/systemd/system/zed_x_daemon.service:/etc/systemd/system/zed_x_daemon.service \
  -e DISPLAY=$DISPLAY \
  -e XAUTHORITY=/root/.Xauthority \
  -e XDG_RUNTIME_DIR=/tmp/runtime-dir \
  samuli-dev:latest bash
```

**Note:** This setup provides direct GMSL camera access. ROS2 wrapper is NOT used - only ZED SDK Python API.

### 3. Verify Installation

Inside the container (conda environment is auto-activated):

```bash
# Check Python version
python --version  # Should show Python 3.11.13

# Check ZED SDK version
python -c "import pyzed.sl as sl; print('ZED SDK version:', sl.Camera.get_sdk_version())"

# List connected cameras
python -c "import pyzed.sl as sl; devices = sl.Camera.get_device_list(); print(f'Found {len(devices)} camera(s)')"

# Verify packages
pip list | grep -E "pyzed|numpy|opencv|nicegui"
```

## Basic Camera Test

### Test Script (save as `test_camera.py`)

```python
#!/usr/bin/env python3
import pyzed.sl as sl

# Create camera object
zed = sl.Camera()

# Set configuration
init_params = sl.InitParameters()
init_params.camera_resolution = sl.RESOLUTION.HD1200  # 1920x1200
init_params.depth_mode = sl.DEPTH_MODE.NEURAL        # AI depth
init_params.coordinate_units = sl.UNIT.METER
init_params.depth_maximum_distance = 20.0             # 20m max

# Open camera
status = zed.open(init_params)
if status != sl.ERROR_CODE.SUCCESS:
    print(f"Camera open failed: {status}")
    exit(1)

print("Camera opened successfully!")

# Get camera information
cam_info = zed.get_camera_information()
print(f"Camera Model: {cam_info.camera_model}")
print(f"Serial Number: {cam_info.serial_number}")
print(f"Camera FW Version: {cam_info.camera_configuration.firmware_version}")

# Close camera
zed.close()
```

Run it:
```bash
python test_camera.py
```

## Troubleshooting

### Camera Not Detected
```bash
# Check ZED daemon status in host
sudo systemctl status zed_x_daemon.service

# Restart daemon in host
sudo systemctl restart zed_x_daemon.service

# In container, check camera with diagnostic tool (do this in GUI, not via ssh!)
/usr/local/zed/tools/ZED_Diagnostic
```

### Import Errors
```bash
# Verify pyzed installation in conda environment
python -c "import pyzed; print(pyzed.__file__)"

# Check PYTHONPATH
echo $PYTHONPATH

# Should include: /usr/local/zed/lib/python3
```