You have to 

authenticate

aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws

docker
docker pull public.ecr.aws/lambda/python:3.11

docker run -it --rm \
  --entrypoint bash \
  -v "$PWD":/var/task \
  public.ecr.aws/lambda/python:3.11

pip install -r requirements.txt -t /var/task/lambda_layers/python
exit


or 

docker run --rm \
  --entrypoint python3.13 \
  -v "$PWD":/var/task \
  public.ecr.aws/lambda/python:3.13 \
  -m pip install -r requirements.txt -t /var/task/lambda_layers/python


then cd into lambda layers zip and replace version

see this: https://www.reddit.com/r/aws/comments/1757d1m/psycopg2_for_aws_lambda_python_311/