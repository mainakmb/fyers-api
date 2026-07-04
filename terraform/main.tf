terraform {
  required_providers {
    utho = {
      source  = "uthoplatforms/utho"
      version = "~> 0.6"
    }
  }
}

provider "utho" {
  token = var.utho_api_token
}

resource "utho_cloud_instance" "trading_bot_server" {
  name            = "mumbai-trading-bot"
  dcslug          = "inmumbaizone2" # Mumbai data center
  planid          = var.plan_id     # Nano tier (1 vCPU, lightweight)
  image           = "ubuntu-22.04-x86_64"
  root_password   = var.root_password
  billingcycle    = "monthly"
  enable_publicip = "true"
}
