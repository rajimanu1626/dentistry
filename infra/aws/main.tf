terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.70"
    }
  }
}

provider "aws" {
  region = var.region
}

locals {
  common_tags = {
    project     = "clinic-crm"
    environment = var.environment
    managed_by  = "terraform"
  }
}
