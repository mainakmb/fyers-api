terraform {
  required_version = ">= 1.5.0"

  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
    external = {
      source  = "hashicorp/external"
      version = "~> 2.3"
    }
  }
}

provider "digitalocean" {
  token = var.do_token
}

locals {
  ssh_private_key_path = startswith(var.pvt_key_path, "~") ? replace(var.pvt_key_path, "~", pathexpand("~")) : var.pvt_key_path
  ssh_public_key_path  = "${local.ssh_private_key_path}.pub"
}

data "external" "ssh_public_key" {
  program = ["python3", "-c", <<-PYTHON
import json
import subprocess
import sys

path = "${local.ssh_private_key_path}"
pub_path = "${local.ssh_public_key_path}"

try:
    with open(pub_path, encoding="utf-8") as handle:
        public_key = handle.read().strip()
except OSError:
    try:
        public_key = subprocess.check_output(
            ["ssh-keygen", "-y", "-f", path],
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        print(json.dumps({"public_key": "", "error": str(exc)}))
        sys.exit(1)

if not public_key:
    print(json.dumps({"public_key": "", "error": "empty SSH public key"}))
    sys.exit(1)

print(json.dumps({"public_key": public_key}))
PYTHON
  ]
}

resource "digitalocean_ssh_key" "trading_key" {
  name       = var.ssh_key_name
  public_key = data.external.ssh_public_key.result.public_key
}

resource "digitalocean_droplet" "trading_bot" {
  image    = var.droplet_image
  name     = var.droplet_name
  region   = var.region
  size     = var.droplet_size
  ssh_keys = [digitalocean_ssh_key.trading_key.fingerprint]

  user_data = <<-EOF
#!/bin/bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python3 python3-pip python3-venv tmux

if [ ! -f /swapfile ]; then
  fallocate -l 1G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=1024
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

grep -q '^vm.swappiness=' /etc/sysctl.conf || echo 'vm.swappiness=10' >> /etc/sysctl.conf
sysctl -w vm.swappiness=10
EOF
}
