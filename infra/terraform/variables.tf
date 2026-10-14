variable "github_owner" {
  description = "GitHub account that owns the FluxSG repository."
  type        = string
  default     = "HninPhyuPhyuAye"
}

variable "github_repository" {
  description = "GitHub repository name."
  type        = string
  default     = "FluxSG"
}

variable "vercel_team_id" {
  description = "Vercel team that owns the existing API project."
  type        = string
  default     = "team_xRGl34kPdrDXfAo3cfAPoZS0"
}

variable "vercel_project_name" {
  description = "Existing Vercel project used by the FastAPI service."
  type        = string
  default     = "fluxsg-api"
}

variable "api_url" {
  description = "Browser-facing production API URL."
  type        = string
  default     = "https://fluxsg-api.vercel.app"
}

variable "forecast_manifest_url" {
  description = "Public guarded forecast manifest consumed by the API."
  type        = string
  default     = "https://hninphyuphyuaye.github.io/FluxSG/data/forecast.json"
}
