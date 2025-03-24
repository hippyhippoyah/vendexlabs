variable "db_user" {
  description = "Database user"
  type        = string
}

variable "db_pass" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "rss_feed_url" {
  description = "RSS feed URL"
  type        = string
}

variable "api_key" {
  description = "API key"
  type        = string
  sensitive   = true
}