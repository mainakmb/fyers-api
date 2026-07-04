variable "utho_api_token" {
  description = "Utho API token (set via GitHub environment secret UTHO_API_TOKEN)"
  type        = string
  sensitive   = true
}

variable "root_password" {
  description = "Root password for the cloud instance (set via GitHub environment secret UTHO_ROOT_PASSWORD)"
  type        = string
  sensitive   = true
}

variable "plan_id" {
  description = "Utho plan ID for the Nano lightweight instance (₹349/mo tier)"
  type        = string
  default     = "10355" # 1 vCPU, 2 GB RAM — smallest basic plan in Mumbai
}
