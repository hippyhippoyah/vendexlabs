provider "aws" {
  region = "us-east-1"
}

# Create a VPC
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}

# Create subnets
resource "aws_subnet" "subnet1" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "us-east-1a"
}

resource "aws_subnet" "subnet2" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "us-east-1b"
}

# Fetch subnet IDs
data "aws_subnet" "subnet1" {
  id = aws_subnet.subnet1.id
}

data "aws_subnet" "subnet2" {
  id = aws_subnet.subnet2.id
}

resource "aws_security_group" "lambda_sg" {
  vpc_id      = aws_vpc.main.id
  name        = "lambda-security-group"
  description = "Security group for Lambda"
}

resource "aws_security_group" "aurora_sg" {
  vpc_id      = aws_vpc.main.id
  name        = "aurora-security-group"
  description = "Allow Lambda access to Aurora"

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda_sg.id]
  }
}

resource "aws_db_subnet_group" "aurora_subnet_group" {
  name       = "aurora-subnet-group"
  subnet_ids = [data.aws_subnet.subnet1.id, data.aws_subnet.subnet2.id]
}

resource "aws_rds_cluster" "aurora" {
  cluster_identifier      = "vendors-aurora"
  engine                  = "aurora-postgresql"
  engine_version          = "15"
  database_name           = "postgres"
  master_username         = "vendorlabs_admin"
  master_password         = "vlabs2025"
  vpc_security_group_ids  = [aws_security_group.aurora_sg.id]
  db_subnet_group_name    = aws_db_subnet_group.aurora_subnet_group.name
  skip_final_snapshot     = true
  serverlessv2_scaling_configuration {
    min_capacity = 0.5
    max_capacity = 4
  }
}

resource "aws_iam_role" "lambda_role" {
  name = "lambda_rds_role"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow"
    }
  ]
}
EOF
}

resource "aws_iam_policy_attachment" "lambda_basic_execution" {
  name       = "lambda_basic_execution"
  roles      = [aws_iam_role.lambda_role.name]
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_policy_attachment" "lambda_vpc_access_execution" {
  name       = "lambda_vpc_access_execution"
  roles      = [aws_iam_role.lambda_role.name]
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_lambda_function" "lambda" {
  function_name    = "lambda-RSS-handler"
  runtime         = "python3.9"
  role            = aws_iam_role.lambda_role.arn
  handler         = "lambda_function.lambda_handler"
  filename        = "../RSS.zip"
  timeout         = 10
  environment {
    variables = {
      DB_HOST     = aws_rds_cluster.aurora.endpoint
      DB_USER     = "admin"
      DB_PASS     = "mysecretpassword"
      DB_NAME     = "postgres"
    }
  }
  vpc_config {
    security_group_ids = [aws_security_group.lambda_sg.id]
    subnet_ids         = [data.aws_subnet.subnet1.id, data.aws_subnet.subnet2.id]
  }
}

# CloudWatch 3h lambda run. Uncomment if needed
# resource "aws_cloudwatch_event_rule" "every_3_hours" {
#   name                = "run-lambda-every-3-hours"
#   schedule_expression = "rate(3 hours)"
# }

# resource "aws_cloudwatch_event_target" "lambda_target" {
#   rule      = aws_cloudwatch_event_rule.every_3_hours.name
#   target_id = "lambda"
#   arn       = aws_lambda_function.lambda.arn
# }

# resource "aws_lambda_permission" "allow_cloudwatch" {
#   statement_id  = "AllowExecutionFromCloudWatch"
#   action        = "lambda:InvokeFunction"
#   function_name = aws_lambda_function.lambda.function_name
#   principal     = "events.amazonaws.com"
#   source_arn    = aws_cloudwatch_event_rule.every_3_hours.arn
# }

output "aurora_endpoint" {
  value = aws_rds_cluster.aurora.endpoint
}

resource "aws_ssm_parameter" "rss_last_published" {
  name  = "/rss/last_published"
  type  = "String"
  value = "2000-01-01T00:00:00Z"  # Initial value
}