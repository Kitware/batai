# Models

```bash
docker build -t batai:training .
```

```bash
docker run \
  -it \
  -d \
  --name batai \
  --gpus=all \
  --shm-size=32gb \
  -v $(pwd):/workspace \
  --entrypoint /bin/bash \
  pytorch/pytorch:2.1.2-cuda11.8-cudnn8-devel
```
