output "droplet_id" {
  description = "DigitalOcean droplet ID"
  value       = digitalocean_droplet.trading_bot_server.id
}

output "public_ip" {
  description = "Public IPv4 address of the trading bot server"
  value       = digitalocean_droplet.trading_bot_server.ipv4_address
}

output "droplet_status" {
  description = "Current status of the droplet"
  value       = digitalocean_droplet.trading_bot_server.status
}

output "region" {
  description = "Region where the droplet is deployed"
  value       = digitalocean_droplet.trading_bot_server.region
}
