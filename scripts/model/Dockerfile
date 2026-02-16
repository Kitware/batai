FROM pytorch/pytorch:2.1.2-cuda11.8-cudnn8-devel

# apt install nvtop htop vim

RUN set -ex \
 && pip install --no-cache-dir -e .[dev]

WORKDIR /app

COPY . /app
