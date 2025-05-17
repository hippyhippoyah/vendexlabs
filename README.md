# VendexLabs


## Overview
Current Iteration (V1.1) sends email notifications 

## Features
- **Infrastructure as Code (IaC)**: Terraform scripts to provision AWS resources.
- **Logging & Monitoring**: AWS CloudWatch integration.
- **Security Best Practices**: IAM roles, security groups, and encryption enabled.
- **Scalability**: Auto-scaling and load balancing configurations.

## Architecture
A simplified diagram of the main parts
![AWS Architecture Diagram](aws-architecture.png)


## Getting Started
### Prerequisites
- AWS CLI installed and configured
- Terraform installed: https://developer.hashicorp.com/terraform/tutorials/aws-get-started

### Deployment Steps
1. Clone the repository:
   ```sh
   git clone https://github.com/hippyhippoyah/vendexlabs.git
   cd vendexlabs/
   ```
2. Create Zip files for RSS, RSS_lambda_layers, and Subscription Lambda
```
zip -r ../RSS-v___.zip .
```
You will also need to package the requirements for the lambda for the lambda layers
```
pip install -r ../requirements.txt -t python/lib/python3.9/site-packages/    
```
3. Create a terraform.tfvars file

```
db_user      = "your_info"
db_pass      = "your_info"
rss_feed_urls = ["https://feeds.feedburner.com/TheHackersNews?format=xml", 
"https://krebsonsecurity.com/feed/", "https://www.bleepingcomputer.com/feed/", 
"https://databreaches.net/feed/", "https://feeds.feedburner.com/eset/blog", 
"https://www.schneier.com/feed/atom/", "https://podcast.darknetdiaries.com/",]
api_key      = "ur_openai_key"
lambda_version = "your_version"
subscription_version = "your_version"
```
4. run terraform apply
5. You will need to connect to the bastion host (EC2 instance in public subnet) to initiallize the tables 
(Sorry I forgot to add to the diagram), you will need to run the query in rss_feeds.sql.  
6. Create API gateway in aws console with your custom needs connected to the subscription lambda. 


## Versions
V1.1: Added parsing for 8 feeds sending email to subscribers every 3h for their subscribed vendors. 

## Todo for next version
- Add additional finds to table
- Add frontend
- modify table to fit needs
- Still very much a WIP will clean up Repo before public (random files not needed and might be sensitive)