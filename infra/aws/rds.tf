resource "aws_db_subnet_group" "crm" {
  name       = "clinic-crm-${var.environment}"
  subnet_ids = aws_subnet.private[*].id
  tags       = local.common_tags
}

resource "aws_security_group" "rds" {
  name        = "clinic-crm-rds-${var.environment}"
  description = "Postgres access from the API ECS service only"
  vpc_id      = aws_vpc.this.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.api.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.common_tags
}

resource "aws_db_parameter_group" "pg16" {
  name   = "clinic-crm-pg16-${var.environment}"
  family = "postgres16"

  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements,pgaudit"
  }

  parameter {
    name  = "pgaudit.log"
    value = "ddl,write"
  }
}

resource "aws_db_instance" "crm" {
  identifier              = "clinic-crm-${var.environment}"
  engine                  = "postgres"
  engine_version          = "16"
  instance_class          = var.db_instance_class
  allocated_storage       = 20
  max_allocated_storage   = 200
  storage_encrypted       = true
  username                = var.db_username
  password                = var.db_password
  db_name                 = "crm"
  parameter_group_name    = aws_db_parameter_group.pg16.name
  db_subnet_group_name    = aws_db_subnet_group.crm.name
  vpc_security_group_ids  = [aws_security_group.rds.id]
  publicly_accessible     = false
  backup_retention_period = 14
  delete_automated_backups = false
  deletion_protection     = true
  skip_final_snapshot     = false
  final_snapshot_identifier = "clinic-crm-${var.environment}-final"
  apply_immediately       = false
  performance_insights_enabled = true
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  tags = local.common_tags
}

output "database_endpoint" {
  value     = aws_db_instance.crm.endpoint
  sensitive = false
}
