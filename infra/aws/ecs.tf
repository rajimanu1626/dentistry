resource "aws_ecs_cluster" "this" {
  name = "clinic-crm-${var.environment}"
  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/clinic-crm-api-${var.environment}"
  retention_in_days = 30
  tags              = local.common_tags
}

resource "aws_iam_role" "task_exec" {
  name = "clinic-crm-task-exec-${var.environment}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = { Service = "ecs-tasks.amazonaws.com" },
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "task_exec_managed" {
  role       = aws_iam_role.task_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "task" {
  name = "clinic-crm-task-${var.environment}"
  assume_role_policy = aws_iam_role.task_exec.assume_role_policy
}

resource "aws_ecs_task_definition" "api" {
  family                   = "clinic-crm-api-${var.environment}"
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn       = aws_iam_role.task_exec.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name      = "api",
      image     = var.api_image,
      essential = true,
      portMappings = [{ containerPort = 8000 }],
      environment = [
        { name = "APP_ENV", value = "production" }
      ],
      secrets = [
        # All secrets supplied via Secrets Manager (DATABASE_URL, JWKS_URL,
        # PHI_ENCRYPTION_KEY, EXTERNAL_SHARE_HMAC_SECRET, S3_*).
      ],
      logConfiguration = {
        logDriver = "awslogs",
        options = {
          awslogs-group         = aws_cloudwatch_log_group.api.name,
          awslogs-region        = var.region,
          awslogs-stream-prefix = "api"
        }
      }
    }
  ])

  tags = local.common_tags
}

resource "aws_ecs_service" "api" {
  name            = "clinic-crm-api-${var.environment}"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.api.id]
    assign_public_ip = false
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  tags = local.common_tags
}
