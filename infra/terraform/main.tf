provider "github" {
  owner = var.github_owner
}

provider "vercel" {
  team = var.vercel_team_id
}

data "github_repository" "fluxsg" {
  full_name = "${var.github_owner}/${var.github_repository}"
}

resource "github_repository_environment" "forecast_production" {
  repository  = data.github_repository.fluxsg.name
  environment = "forecast-production"
}

resource "github_actions_environment_variable" "api_url" {
  repository    = data.github_repository.fluxsg.name
  environment   = github_repository_environment.forecast_production.environment
  variable_name = "FLUXSG_API_URL"
  value         = var.api_url
}

resource "github_actions_environment_variable" "forecast_manifest_url" {
  repository    = data.github_repository.fluxsg.name
  environment   = github_repository_environment.forecast_production.environment
  variable_name = "FORECAST_MANIFEST_URL"
  value         = var.forecast_manifest_url
}

data "vercel_project" "api" {
  name = var.vercel_project_name
}

resource "vercel_project_environment_variable" "forecast_manifest_url" {
  project_id = data.vercel_project.api.id
  key        = "FORECAST_MANIFEST_URL"
  value      = var.forecast_manifest_url
  target     = ["production", "preview", "development"]
  sensitive  = false
}
