variable "do_token" {
  description = "DigitalOcean API token (set via GitHub secret DIGITALOCEAN_TOKEN or TF_VAR_do_token)"
  type        = string
  sensitive   = true
}

variable "pvt_key_path" {
  description = "Path to the SSH private key; the matching .pub file is registered with DigitalOcean"
  type        = string
}

variable "droplet_name" {
  description = "Name of the trading bot droplet"
  type        = string
  default     = "mumbai-trading-bot"
}

variable "region" {
  description = "DigitalOcean region slug (blr1 is closest to Mumbai)"
  type        = string
  default     = "blr1"
}

variable "droplet_size" {
  description = "DigitalOcean droplet size slug"
  type        = string
  default     = "s-1vcpu-1gb"
}

variable "droplet_image" {
  description = "DigitalOcean droplet image slug"
  type        = string
  default     = "ubuntu-22-04-x86_64"
}

variable "ssh_key_name" {
  description = "Label for the SSH key uploaded to DigitalOcean"
  type        = string
  default     = "fyers-api-trading-bot"
}

variable "droplet_tags" {
  description = "Tags applied to the droplet"
  type        = list(string)
  default     = ["fyers-api", "trading-bot"]
}
