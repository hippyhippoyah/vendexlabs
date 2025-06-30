# Vendexlabs Infra

## Setup

1. **Install Terraform**: https://www.terraform.io/downloads.html
2. **Configure AWS Credentials**: Use environment variables, AWS CLI, or `~/.aws/credentials`.
3. **Set Secrets**:  
   Export required variables before running Terraform:
   ```
   export TF_VAR_db_user=youruser
   export TF_VAR_db_pass=yourpass
   ```
4. **Remote State**:  
   Ensure you have access to the S3 bucket and DynamoDB table for state and locking.

5. **Run Terraform**:
   ```
   terraform init
   terraform plan
   terraform apply
   ```
