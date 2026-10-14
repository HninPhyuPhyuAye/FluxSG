terraform {
  required_version = ">= 1.10.0"

  required_providers {
    github = {
      source  = "integrations/github"
      version = "6.13.0"
    }
    vercel = {
      source  = "vercel/vercel"
      version = "5.17.1"
    }
  }
}
