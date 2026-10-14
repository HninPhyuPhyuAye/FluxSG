output "github_environment" {
  description = "GitHub Actions environment protecting forecast publication."
  value       = github_repository_environment.forecast_production.environment
}

output "vercel_project_id" {
  description = "Existing Vercel API project managed by this configuration."
  value       = data.vercel_project.api.id
}

output "forecast_manifest_url" {
  description = "Manifest URL configured in GitHub Actions and Vercel."
  value       = var.forecast_manifest_url
}
