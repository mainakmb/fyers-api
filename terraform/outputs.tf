output "instance_id" {
  description = "Utho cloud instance ID"
  value       = utho_cloud_instance.trading_bot_server.id
}

output "public_ip" {
  description = "Public IP address of the trading bot server"
  value       = utho_cloud_instance.trading_bot_server.ip
}

output "instance_status" {
  description = "Current status of the cloud instance"
  value       = utho_cloud_instance.trading_bot_server.status
}
