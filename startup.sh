#!/bin/bash

echo "--- INSTALANDO LIBRERIAS DE SISTEMA ---"
apt-get update
apt-get install -y libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev libxcb1

echo "--- INSTALANDO PYTHON PACKAGES ---"
pip install --upgrade pip --break-system-packages
pip install opencv-python-headless websockets numpy --break-system-packages

echo "--- ARRANCANDO MAIN.PY ---"
python3 main.py
