variable "region" {
  type    = string
  default = "ap-south-1" # Mumbai, DPDP-friendly
}

variable "environment" {
  type    = string
  default = "prod"
}

variable "db_username" {
  type    = string
  default = "crm_admin"
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "vpc_cidr" {
  type    = string
  default = "10.42.0.0/16"
}

variable "api_image" {
  description = "ghcr.io/.../clinic-crm-api:<tag> — same image that runs on Fly."
  type        = string
}

variable "api_desired_count" {
  type    = number
  default = 1
}

variable "domain_name" {
  type    = string
  default = ""
}
