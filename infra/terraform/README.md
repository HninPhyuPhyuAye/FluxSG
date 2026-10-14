# Production infrastructure

Terraform manages the `forecast-production` GitHub environment, its public
deployment variables, and the forecast-manifest URL attached to the existing
Vercel API project. Secrets remain outside Terraform state.

Authentication is read from `GITHUB_TOKEN` and `VERCEL_API_TOKEN`.

```bash
terraform init
terraform plan
terraform apply
```

The state is local for this portfolio environment and is ignored by Git. A
team deployment should move it to an encrypted remote backend with locking.
