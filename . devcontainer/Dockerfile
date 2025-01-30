
FROM mcr.microsoft.com/devcontainers/python:3.11

RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libxcb-xinerama0

ENV QT_QPA_PLATFORM=offscreen
