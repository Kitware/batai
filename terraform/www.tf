locals {
  www_env_vars = {
    VITE_API_ROOT = "https://${module.django.fqdn}"
  }
}

data "cloudflare_account" "this" {
  # Kitware
  account_id = "b7ba799b50a979650d3362e965257042"
}

resource "cloudflare_pages_project" "www" {
  account_id        = data.cloudflare_account.this.id
  name              = "bats-ai"
  production_branch = "main"

  source = {
    type = "github"
    config = {
      production_branch = "main"
      owner             = "Kitware"
      repo_name         = "batai"
      path_includes     = ["client/*"]
    }
  }

  build_config = {
    build_caching   = true
    root_dir        = "client"
    build_command   = "npm run build"
    destination_dir = "dist"
  }

  deployment_configs = {
    preview = {
      env_vars = {
        for k, v in local.www_env_vars : k => {
          type  = "plain_text"
          value = v
        }
      }
    }
    production = {
      env_vars = merge(
        {
          for k, v in local.www_env_vars : k => {
            type  = "plain_text"
            value = v
          }
        },
        {
          VITE_SENTRY_DSN = {
            type  = "plain_text"
            value = "https://a224627951abd0f0606d8578cacef5d6@o267860.ingest.us.sentry.io/4510829950730240"
          }
          SENTRY_AUTH_TOKEN = {
            type  = "secret_text"
            value = var.SENTRY_AUTH_TOKEN
          }
        },
      )
    }
  }
}

resource "cloudflare_pages_domain" "www" {
  account_id   = data.cloudflare_account.this.id
  project_name = cloudflare_pages_project.www.name
  name         = aws_route53_record.www.fqdn
}

resource "aws_route53_record" "www" {
  zone_id = data.aws_route53_zone.this.zone_id
  name    = "www"
  type    = "CNAME"
  ttl     = 300
  records = [cloudflare_pages_project.www.subdomain]
}
