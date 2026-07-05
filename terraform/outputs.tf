output "server_static_ip" {
  value       = digitalocean_droplet.trading_bot.ipv4_address
  description = "The static IP to whitelist with your broker"
}
