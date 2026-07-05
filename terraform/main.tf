terraform {
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
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

resource "digitalocean_ssh_key" "trading_bot" {
  name       = var.ssh_key_name
  public_key = file(local.ssh_public_key_path)
}

resource "digitalocean_droplet" "trading_bot_server" {
  name     = var.droplet_name
  region   = var.region
  size     = var.droplet_size
  image    = var.droplet_image
  ssh_keys = [digitalocean_ssh_key.trading_bot.fingerprint]

  tags = var.droplet_tags
}
