provider "aws" {
  region = "us-east-1"
}

terraform {
  backend "s3" {
    bucket         = "vendexlabs-infra-bucket"
    key            = "vendexlabs/infra/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-lock-table"
    encrypt        = true
  }
}


# resource "aws_vpc" "main" {
#   cidr_block = "10.0.0.0/16"
# }

# resource "aws_subnet" "subnet1" {
#   vpc_id            = aws_vpc.main.id
#   cidr_block        = "10.0.1.0/24"
#   availability_zone = "us-east-1a"
# }

# resource "aws_subnet" "subnet2" {
#   vpc_id            = aws_vpc.main.id
#   cidr_block        = "10.0.2.0/24"
#   availability_zone = "us-east-1b"
#   map_public_ip_on_launch = true
# }

# data "aws_subnet" "subnet1" {
#   id = aws_subnet.subnet1.id
# }

# data "aws_subnet" "subnet2" {
#   id = aws_subnet.subnet2.id
# }

# resource "aws_internet_gateway" "igw" {
#   vpc_id = aws_vpc.main.id
# }


# resource "aws_route_table" "public_rt" {
#   vpc_id = aws_vpc.main.id

#   route {
#     cidr_block = "0.0.0.0/0"
#     gateway_id = aws_internet_gateway.igw.id
#   }
# }

# resource "aws_route_table_association" "subnet2_association" {
#   subnet_id      = aws_subnet.subnet2.id
#   route_table_id = aws_route_table.public_rt.id
# }

# resource "aws_security_group" "lambda_sg" {
#   vpc_id      = aws_vpc.main.id
#   name        = "lambda-security-group"
#   description = "Security group for Lambda"

#   ingress {
#     from_port   = 5432
#     to_port     = 5432
#     protocol    = "tcp"
#     cidr_blocks = ["10.0.0.0/16"]  # Allow traffic from the VPC
#   }

#   egress {
#     from_port   = 0
#     to_port     = 0
#     protocol    = "-1"
#     cidr_blocks = ["0.0.0.0/0"]
#   }
# }

# resource "aws_security_group" "aurora_sg" {
#   vpc_id      = aws_vpc.main.id
#   name        = "aurora-security-group"
#   description = "Allow Lambda access to Aurora"

#   ingress {
#     from_port       = 5432
#     to_port         = 5432
#     protocol        = "tcp"
#     cidr_blocks     = ["10.0.0.0/16"]  # Allow traffic from the VPC
#   }

#   egress {
#     from_port   = 0
#     to_port     = 0
#     protocol    = "-1"
#     cidr_blocks = ["0.0.0.0/0"]
#   }
# }

# resource "aws_db_subnet_group" "aurora_subnet_group" {
#   name       = "aurora-subnet-group"
#   subnet_ids = [data.aws_subnet.subnet1.id, data.aws_subnet.subnet2.id]
# }

# resource "aws_rds_cluster" "ven_aurora" {
#   cluster_identifier      = "vendors-aurora"
#   engine                  = "aurora-postgresql"
#   engine_mode             = "provisioned"
#   engine_version          = "13.18"
#   database_name           = "postgres"
#   master_username         = var.db_user
#   master_password         = var.db_pass
#   vpc_security_group_ids  = [aws_security_group.aurora_sg.id]
#   db_subnet_group_name    = aws_db_subnet_group.aurora_subnet_group.name
#   storage_encrypted       = true
#   skip_final_snapshot     = true

#   serverlessv2_scaling_configuration {
#     min_capacity = 0.5 
#     max_capacity = 4
#   }
# }

# resource "aws_rds_cluster_instance" "aurora_instance" {
#   cluster_identifier = aws_rds_cluster.ven_aurora.id
#   instance_class     = "db.serverless"
#   engine             = aws_rds_cluster.ven_aurora.engine
#   engine_version     = aws_rds_cluster.ven_aurora.engine_version
#   publicly_accessible = false
# }

# output "aurora_endpoint" {
#   value = aws_rds_cluster.ven_aurora.endpoint
# }

output "rds_endpoint" {
  value = aws_db_instance.ven_rds.endpoint
}
# --- Use default VPC and subnets ---
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

data "aws_security_group" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  filter {
    name   = "group-name"
    values = ["default"]
  }
}


# --- New RDS instance in default VPC ---
resource "aws_db_instance" "ven_rds" {
  identifier              = "vendors-postgres"
  engine                  = "postgres"
  engine_version          = "17.6"
  instance_class          = "db.t4g.micro"
  allocated_storage       = 20
  db_name                 = "postgres"
  username                = var.db_user
  password                = var.db_pass
  vpc_security_group_ids  = [data.aws_security_group.default.id]
  db_subnet_group_name    = null # Use default
  publicly_accessible     = false
  skip_final_snapshot     = true
  storage_encrypted       = false
  multi_az                = false
}