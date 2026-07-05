variable "do_token" {
  type        = string
  description = "Your DigitalOcean Personal Access Token"
  sensitive   = true

  validation {
    condition     = length(trimspace(var.do_token)) > 0
    error_message = "do_token must not be empty."
  }
}

variable "pvt_key_path" {
  type        = string
  description = "Local path to your private SSH key (e.g., ~/.ssh/id_ed25519)"
  default     = "~/.ssh/id_ed25519"
}

variable "droplet_name" {
  type        = string
  description = "DigitalOcean droplet name"
  default     = "mumbai-trading-node"
}

variable "region" {
  type        = string
  description = "DigitalOcean region slug"
  default     = "blr1"
}

variable "droplet_size" {
  type        = string
  description = "DigitalOcean droplet size slug"
  default     = "s-1vcpu-512mb-10gb"
}

variable "droplet_image" {
  type        = string
  description = "DigitalOcean droplet image slug"
  default     = "ubuntu-24-04-x64"
}

variable "ssh_key_name" {
  type        = string
  description = "Name for the SSH key registered in DigitalOcean"
  default     = "trading-bot-ssh-key"
}
