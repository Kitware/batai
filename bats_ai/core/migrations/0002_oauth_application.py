from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import migrations

if TYPE_CHECKING:
    from django.db.backends.base.schema import BaseDatabaseSchemaEditor
    from django.db.migrations.state import StateApps

APPLICATION_NAME = "batsai-client"
CLIENT_ID = "HSJWFZ2cIpWQOvNyCXyStV9hiOd7DfWeBOCzo4pP"


def create_oauth2_application(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    Application = apps.get_model("oauth2_provider", "Application")

    Application.objects.create(
        name=APPLICATION_NAME,
        client_id=CLIENT_ID,
        user=None,
        redirect_uris="http://localhost:8080/",
        client_type="public",
        authorization_grant_type="authorization-code",
        # Trust our own client, so don't require users to consent.
        skip_authorization=True,
        client_secret="",
        # No need to set "allowed_origins", we provide CORS via "django-cors-headers".
        # No need to set "post_logout_redirect_uris", we don't use RP-initiated logout.
    )


def delete_oauth2_application(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    Application = apps.get_model("oauth2_provider", "Application")

    Application.objects.filter(name=APPLICATION_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_default_site"),
        # This is the final oauth2_provider app migration
        ("oauth2_provider", "0010_application_allowed_origins"),
    ]

    operations = [
        migrations.RunPython(create_oauth2_application, delete_oauth2_application),
    ]
