#!/usr/bin/env bash
set -e

HOST="$1"
if [[ -z "$HOST" ]]; then
    echo "Usage: $0 <ec2-ip-address>"
    exit 1
fi

SSH_TARGET="ubuntu@$HOST"

echo "==> Fetching secrets from Heroku..."
ENV_FILE=$(mktemp)
heroku config --app bats-ai --shell > "$ENV_FILE"

echo "==> Uploading env file to remote machine..."
scp "$ENV_FILE" "$SSH_TARGET:/home/ubuntu/batai.prod.env"
rm "$ENV_FILE"

echo "==> Installing system packages..."
ssh "$SSH_TARGET" 'sudo apt-get update && sudo apt-get install -y curl git'

echo "==> Installing uv..."
ssh "$SSH_TARGET" 'curl -LsSf https://astral.sh/uv/install.sh | sudo UV_INSTALL_DIR=/usr/local/bin sh'

echo "==> Cloning repository..."
ssh "$SSH_TARGET" 'git clone https://github.com/Kitware/batai.git /home/ubuntu/batai'

echo "==> Adding SOURCE_VERSION to env file..."
ssh "$SSH_TARGET" 'echo "SOURCE_VERSION=$(git -C /home/ubuntu/batai rev-parse HEAD)" >> /home/ubuntu/batai.prod.env'

echo "==> Installing Python dependencies..."
ssh "$SSH_TARGET" 'cd /home/ubuntu/batai && uv sync --extra tasks'

echo "==> Creating systemd service..."
ssh "$SSH_TARGET" 'sudo tee /etc/systemd/system/celery.service > /dev/null' << 'EOF'
[Unit]
Description=Celery Service
After=network.target

[Service]
User=ubuntu
Group=ubuntu

WorkingDirectory=/home/ubuntu/batai

Environment=LC_ALL=C.UTF-8
Environment=LANG=C.UTF-8

# Application config environment
EnvironmentFile=/home/ubuntu/batai.prod.env

ExecStart=/usr/local/bin/uv run --extra tasks \
  celery \
  --app bats_ai.celery \
  worker \
  --loglevel INFO \
  --without-heartbeat

TimeoutStopSec=90s
# Only SIGTERM the main process, since Celery is pre-fork by default
KillMode=mixed

Restart=always

[Install]
WantedBy=multi-user.target
EOF

echo "==> Enabling and starting celery service..."
ssh "$SSH_TARGET" 'sudo systemctl daemon-reload && sudo systemctl enable celery && sudo systemctl start celery'

echo "==> Done! Celery worker is running on $HOST"
