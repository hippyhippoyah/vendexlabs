variable "db_user" {
  description = "Database user"
  type        = string
}

variable "db_pass" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "rss_feed_urls" {
  description = "RSS feed URL"
  type        = list(string)
}

variable "api_key" {
  description = "API key"
  type        = string
  sensitive   = true
}

variable "lambda_version" {
  description = "Lambda version"
  type        = string
}

variable "subscription_version" {
  description = "Subscription version"
  type        = string
}