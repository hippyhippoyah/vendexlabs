resource "aws_iam_role" "ssm_ec2_role" {
  name = "ssm-ec2-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ssm_managed_policy" {
  role       = aws_iam_role.ssm_ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "ssm_instance_profile" {
  name = "ssm-instance-profile"
  role = aws_iam_role.ssm_ec2_role.name
}

resource "aws_security_group" "bastion_sg" {
  vpc_id      = aws_vpc.main.id
  name        = "bastion-sg"
  description = "Allow SSM and Aurora access"

  # Allow outbound to Aurora port
  egress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    security_groups = [aws_security_group.aurora_sg.id]
  }

  # Allow all outbound for SSM
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "bastion" {
  ami                    = "ami-0c02fb55956c7d316" # Amazon Linux 2 in us-east-1
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.subnet1.id
  vpc_security_group_ids = [aws_security_group.bastion_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.ssm_instance_profile.name

  tags = {
    Name = "ssm-bastion"
  }
}

# (Optional) VPC endpoints for SSM in private subnet
resource "aws_vpc_endpoint" "ssm" {
  vpc_id       = aws_vpc.main.id
  service_name = "com.amazonaws.us-east-1.ssm"
  subnet_ids   = [aws_subnet.subnet1.id]
  security_group_ids = [aws_security_group.bastion_sg.id]
  vpc_endpoint_type = "Interface"
}

resource "aws_vpc_endpoint" "ssmmessages" {
  vpc_id       = aws_vpc.main.id
  service_name = "com.amazonaws.us-east-1.ssmmessages"
  subnet_ids   = [aws_subnet.subnet1.id]
  security_group_ids = [aws_security_group.bastion_sg.id]
  vpc_endpoint_type = "Interface"
}

resource "aws_vpc_endpoint" "ec2messages" {
  vpc_id       = aws_vpc.main.id
  service_name = "com.amazonaws.us-east-1.ec2messages"
  subnet_ids   = [aws_subnet.subnet1.id]
  security_group_ids = [aws_security_group.bastion_sg.id]
  vpc_endpoint_type = "Interface"
}