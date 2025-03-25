provider "aws" {
  region = "us-east-1"
}


resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}

resource "aws_subnet" "subnet1" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "us-east-1a"
}

resource "aws_subnet" "subnet2" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "us-east-1b"
  map_public_ip_on_launch = true
}

data "aws_subnet" "subnet1" {
  id = aws_subnet.subnet1.id
}

data "aws_subnet" "subnet2" {
  id = aws_subnet.subnet2.id
}

# Create an Internet Gateway
resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
}

# Create a Route Table
resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
}

# Associate the Route Table with subnet2
resource "aws_route_table_association" "subnet2_association" {
  subnet_id      = aws_subnet.subnet2.id
  route_table_id = aws_route_table.public_rt.id
}

# Create a security group for the bastion host
resource "aws_security_group" "bastion_sg" {
  vpc_id = aws_vpc.main.id
  name   = "bastion-security-group"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_key_pair" "bastion_key" {
  key_name   = "bastion-key"
  public_key = file("/Users/johndoe/Downloads/vendex.pub") 
}

# Launch an EC2 instance in subnet2
resource "aws_instance" "bastion" {
  ami           = "ami-08b5b3a93ed654d19"
  instance_type = "t2.micro"
  subnet_id     = aws_subnet.subnet2.id
  vpc_security_group_ids = [aws_security_group.bastion_sg.id]
  associate_public_ip_address = true
  key_name      = aws_key_pair.bastion_key.key_name
  tags = {
    Name = "BastionHost"
  }
}

resource "aws_security_group" "lambda_sg" {
  vpc_id      = aws_vpc.main.id
  name        = "lambda-security-group"
  description = "Security group for Lambda"

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]  # Allow traffic from the VPC
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "aurora_sg" {
  vpc_id      = aws_vpc.main.id
  name        = "aurora-security-group"
  description = "Allow Lambda access to Aurora"

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    cidr_blocks     = ["10.0.0.0/16"]  # Allow traffic from the VPC
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_subnet_group" "aurora_subnet_group" {
  name       = "aurora-subnet-group"
  subnet_ids = [data.aws_subnet.subnet1.id, data.aws_subnet.subnet2.id]
}

resource "aws_rds_cluster" "ven_aurora" {
  cluster_identifier      = "vendors-aurora"
  engine                  = "aurora-postgresql"
  engine_mode             = "provisioned"
  engine_version          = "13.9"
  database_name           = "postgres"
  master_username         = var.db_user
  master_password         = var.db_pass
  vpc_security_group_ids  = [aws_security_group.aurora_sg.id]
  db_subnet_group_name    = aws_db_subnet_group.aurora_subnet_group.name
  storage_encrypted       = true

  serverlessv2_scaling_configuration {
    min_capacity = 0.5
    max_capacity = 4
  }
}

resource "aws_rds_cluster_instance" "example1" {
  cluster_identifier = aws_rds_cluster.ven_aurora.id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.ven_aurora.engine
  engine_version     = aws_rds_cluster.ven_aurora.engine_version
  publicly_accessible = false
}

resource "aws_iam_role" "vl_lambda_role" {
  name = "vl_lambda_rds_role"

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
  roles      = [aws_iam_role.vl_lambda_role.name]
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_policy_attachment" "lambda_vpc_access_execution" {
  name       = "lambda_vpc_access_execution"
  roles      = [aws_iam_role.vl_lambda_role.name]
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_lambda_layer_version" "rss_layer" {
  filename         = "../RSS-layers.zip"
  layer_name       = "rss_layer"
  compatible_runtimes = ["python3.9"]
}

resource "aws_lambda_function" "lambda" {
  function_name    = "lambda-RSS-handler"
  runtime         = "python3.9"
  role            = aws_iam_role.vl_lambda_role.arn
  handler         = "parser.lambda_handler"
  filename        = "../RSS-${var.lambda_version}.zip"
  timeout         = 120
  memory_size     = 1024
  layers           = [aws_lambda_layer_version.rss_layer.arn]
  environment {
    variables = {
      DB_HOST     = aws_rds_cluster.ven_aurora.endpoint
      DB_USER     = var.db_user
      DB_PASS     = var.db_pass
      DB_NAME     = "postgres"
      RSS_FEED_URL = var.rss_feed_url
      API_KEY     = var.api_key
    }
  }
  vpc_config {
    security_group_ids = [aws_security_group.lambda_sg.id]
    subnet_ids         = [data.aws_subnet.subnet1.id, data.aws_subnet.subnet2.id]
  }
}

resource "aws_lambda_function" "subscribe_lambda" {
  function_name    = "lambda-subscribe-handler"
  runtime         = "python3.9"
  role            = aws_iam_role.vl_lambda_role.arn
  handler         = "subscribe.lambda_handler"
  filename        = "../Subscription-${var.subscription_version}.zip"
  timeout         = 120
  memory_size     = 1024
  layers          = [aws_lambda_layer_version.rss_layer.arn]
  environment {
    variables = {
      DB_HOST     = aws_rds_cluster.ven_aurora.endpoint
      DB_USER     = var.db_user
      DB_PASS     = var.db_pass
      DB_NAME     = "postgres"
    }
  }
  vpc_config {
    security_group_ids = [aws_security_group.lambda_sg.id]
    subnet_ids         = [data.aws_subnet.subnet1.id, data.aws_subnet.subnet2.id]
  }
}

output "aurora_endpoint" {
  value = aws_rds_cluster.ven_aurora.endpoint
}