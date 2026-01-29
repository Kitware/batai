data "aws_route53_zone" "this" {
  # This must be created by hand in the AWS console
  name = "bateval.com"
}

data "heroku_team" "this" {
  name = "kitware"
}

module "django" {
  source  = "kitware-resonant/resonant/heroku"
  version = "3.1.0"

  project_slug           = "bats-ai"
  route53_zone_id        = data.aws_route53_zone.this.zone_id
  heroku_team_name       = data.heroku_team.this.name
  subdomain_name         = "api"
  django_settings_module = "bats_ai.settings.heroku_production"
}
