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

- API Gateway and Cognito are managed externally. 


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
2. Create a terraform.tfvars file

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
6. To expose the lambda, configure your own API gateway and Cognito. Some lambdas like subscription manager require cognito and token parsing.


## Versions
#### 1.0 
   - Basic Subscription Handler to send Feeds
#### 1.01 
   - Infra Setup with NAT Gateway, Private VPC and subnet, and 2 Lambdas with API Gateway
   - individual subscriptions management
   - rss feed parsing
#### 1.02 
   - Frontend Vendex-labs client added to support the endpoints
#### 1.03
   - Bug Fixes with RSS feed parser and email sender

#### 1.1
   - Vendor Info Parser Basic with OpenAI and google search
#### 1.2
   - Add support for Org Management
   - Account Manager
   - Subscription Manager
   - User Manager
   - Subscription List Manager
#### 1.21
   - Refactor RSS parse to support new system
#### 1.3
   - Vendor Info upgrade with perplexity, and custom search
#### 1.31
   -Upgrade 3.9 to Python 3.13
#### 1.4
   - Descaled to use default VPC and t4.micro instead of Aurora and NAT. EST cost: $100m -> $20/m 

#### 1.5
   - Assesment Tracking Added (WIP)

## Future Improvements
[google doc](https://docs.google.com/document/d/1bhuVU0c1opEizm29kJ56zAv7SG-uy6hAinnJpCYExks)
