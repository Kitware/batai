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

  project_slug           = "bats-ai"
  route53_zone_id        = data.aws_route53_zone.this.zone_id
  heroku_team_name       = data.heroku_team.this.name
  subdomain_name         = "api"
  django_settings_module = "bats_ai.settings.heroku_production"

  additional_django_vars = {
    DJANGO_SENTRY_DSN = "https://6949e99cb9fcea56cfbb36954d4de266@o267860.ingest.us.sentry.io/4509271243423744"

  }
}
