resource "aws_cognito_user_pool" "users" {
  name = "clinic-crm-${var.environment}-users"

  password_policy {
    minimum_length    = 12
    require_lowercase = true
    require_uppercase = true
    require_numbers   = true
    require_symbols   = false
  }

  mfa_configuration = "OPTIONAL"

  software_token_mfa_configuration {
    enabled = true
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  schema {
    name                = "email"
    attribute_data_type = "String"
    required            = true
    mutable             = false
  }

  tags = local.common_tags
}

resource "aws_cognito_user_pool_client" "web" {
  name         = "clinic-crm-${var.environment}-web"
  user_pool_id = aws_cognito_user_pool.users.id
  generate_secret = false

  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH"
  ]
}

output "cognito_user_pool_id" {
  value = aws_cognito_user_pool.users.id
}

output "cognito_user_pool_jwks" {
  value = "https://cognito-idp.${var.region}.amazonaws.com/${aws_cognito_user_pool.users.id}/.well-known/jwks.json"
}
