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

# Yes im lazy, full access it is. Change later
resource "aws_iam_policy_attachment" "attach_ses_full_access" {
  name       = "attach_ses_full_access"
  roles      = [aws_iam_role.vl_lambda_role.name]
  policy_arn = "arn:aws:iam::aws:policy/AmazonSESFullAccess"
}

resource "aws_lambda_layer_version" "rss_layer" {
  filename         = "../lambda_layersV1.zip"
  layer_name       = "rss_layer"
  compatible_runtimes = ["python3.9"]
}

# Archive the RSS Lambda source code
data "archive_file" "rss_lambda_zip" {
  type        = "zip"
  source_dir  = "../feed_parser_lambda"
  output_path = "${path.module}/RSS-lambda.zip"
}

# Archive the Subscription Lambda source code
data "archive_file" "subscription_lambda_zip" {
  type        = "zip"
  source_dir  = "../subscription_handler_lambda"
  output_path = "${path.module}/Subscription-lambda.zip"
}

# Archive the Vendor Info Lambda source code
data "archive_file" "vendor_info_lambda_zip" {
  type        = "zip"
  source_dir  = "../vendor_info_lambda"
  output_path = "${path.module}/vendor_info-lambda.zip"
}

resource "aws_lambda_function" "lambda" {
  function_name    = "lambda-RSS-handler"
  runtime          = "python3.9"
  role             = aws_iam_role.vl_lambda_role.arn
  handler          = "parser.lambda_handler"
  filename         = data.archive_file.rss_lambda_zip.output_path
  source_code_hash = data.archive_file.rss_lambda_zip.output_base64sha256
  timeout          = 240
  memory_size      = 1024
  layers           = [aws_lambda_layer_version.rss_layer.arn]
  environment {
    variables = {
      DB_HOST     = aws_rds_cluster.ven_aurora.endpoint
      DB_USER     = var.db_user
      DB_PASS     = var.db_pass
      DB_NAME     = "postgres"
      RSS_FEED_URLS = jsonencode(var.rss_feed_urls)
      API_KEY     = var.api_key
    }
  }
  vpc_config {
    security_group_ids = [aws_security_group.lambda_sg.id]
    subnet_ids         = [data.aws_subnet.subnet1.id]
  }
}

resource "aws_lambda_function" "subscribe_lambda" {
  function_name    = "lambda-subscribe-handler"
  runtime          = "python3.9"
  role             = aws_iam_role.vl_lambda_role.arn
  handler          = "subscription_manager.lambda_handler"
  filename         = data.archive_file.subscription_lambda_zip.output_path
  source_code_hash = data.archive_file.subscription_lambda_zip.output_base64sha256
  timeout          = 120
  memory_size      = 1024
  layers           = [aws_lambda_layer_version.rss_layer.arn]
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

resource "aws_lambda_function" "vendor_info_lambda" {
  function_name    = "lambda-vendor-info-handler"
  runtime          = "python3.9"
  role             = aws_iam_role.vl_lambda_role.arn
  handler          = "vendor_info.lambda_handler"
  filename         = data.archive_file.vendor_info_lambda_zip.output_path
  source_code_hash = data.archive_file.vendor_info_lambda_zip.output_base64sha256
  timeout          = 450
  memory_size      = 1024
  layers           = [aws_lambda_layer_version.rss_layer.arn]
  environment {
    variables = {
      DB_HOST     = aws_rds_cluster.ven_aurora.endpoint
      DB_USER     = var.db_user
      DB_PASS     = var.db_pass
      DB_NAME     = "postgres"
      API_KEY     = var.api_key
    }
  }
  vpc_config {
    security_group_ids = [aws_security_group.lambda_sg.id]
    subnet_ids         = [data.aws_subnet.subnet1.id]
  }
}

# NAT Gateway and EIP for Lambda internet access
resource "aws_eip" "nat_eip" {
  domain = "vpc"
}

resource "aws_nat_gateway" "nat_gw" {
  allocation_id = aws_eip.nat_eip.id
  subnet_id     = aws_subnet.subnet2.id
}

resource "aws_route_table" "private_rt" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat_gw.id
  }
}

resource "aws_route_table_association" "subnet1_association" {
  subnet_id      = aws_subnet.subnet1.id
  route_table_id = aws_route_table.private_rt.id
}


# Frequency can be adjusted here
resource "aws_cloudwatch_event_rule" "rss_handler_schedule" {
  name        = "rss-handler-schedule"
  description = "Trigger RSS handler Lambda every 3 hours"
  schedule_expression = "rate(3 hours)"
  state = "ENABLED"
}

resource "aws_cloudwatch_event_target" "rss_handler_target" {
  rule      = aws_cloudwatch_event_rule.rss_handler_schedule.name
  target_id = "rss-handler-lambda"
  arn       = aws_lambda_function.lambda.arn

  input = jsonencode({
    hours = 3
  })
}

resource "aws_lambda_permission" "allow_cloudwatch_to_invoke_rss_handler" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.rss_handler_schedule.arn
}