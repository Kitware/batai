data "aws_route53_zone" "this" {
  # This must be created by hand in the AWS console
  name = "bateval.com"
}

data "heroku_team" "this" {
  name = "kitware"
}

module "django" {
  source  = "kitware-resonant/resonant/heroku"
  version = "3.1.1"

  project_slug                = "bats-ai"
  route53_zone_id             = data.aws_route53_zone.this.zone_id
  heroku_team_name            = data.heroku_team.this.name
  subdomain_name              = "api"
  django_settings_module      = "bats_ai.settings.heroku_production"
  heroku_worker_dyno_quantity = 0

  django_cors_allowed_origins = [
    # Can't make this use "aws_route53_record.www.fqdn" because of a circular dependency
    "https://www.${data.aws_route53_zone.this.name}",
  ]
  django_cors_allowed_origin_regexes = [
    # Can't base this on "cloudflare_pages_project.www.subdomain" because of a circular dependency
    "https://[\\w-]+\\.bats-ai\\.pages\\.dev",
  ]
  additional_django_vars = {
    DJANGO_SENTRY_DSN = "https://5bfdd2a77e7e8cbcea9ea873dbf9cbd6@o267860.ingest.us.sentry.io/4510800443015168"
  }
}
