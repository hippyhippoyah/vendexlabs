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
  description = "RSS feed URLs as a list of objects"
  type = list(object({
    source = string
    url    = string
  }))
}

variable "api_key" {
  description = "API key"
  type        = string
  sensitive   = true
}

variable "google_api_key" {
  description = "Google Custom Search API key"
  type        = string
  sensitive   = true
}

variable "google_cse_id" {
  description = "Google Custom Search Engine ID"
  type        = string
}

variable "google_search_url" {
  description = "Google Custom Search API URL"
  type        = string
  default     = "https://www.googleapis.com/customsearch/v1"
}

variable "openai_api_url" {
  description = "OpenAI API URL"
  type        = string
  default     = "https://api.openai.com/v1/chat/completions"
}

variable "perplexity_api_key" {
  description = "Perplexity AI API key"
  type        = string
  sensitive   = true
}

variable "perplexity_api_url" {
  description = "Perplexity AI API URL"
  type        = string
  default     = "https://api.perplexity.ai/chat/completions"
}