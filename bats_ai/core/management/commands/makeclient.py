import os

from django.contrib.auth.models import User
import djclick as click
from oauth2_provider.models import Application

CLIENT_ID = os.environ.get('APPLICATION_CLIENT_ID', 'HSJWFZ2cIpWQOvNyCXyStV9hiOd7DfWeBOCzo4pP')


# create django oauth toolkit appliction (client)
@click.option(
    '--username',
    type=click.STRING,
    required=True,
    help='superuser username for application creator',
)
@click.option(
    '--uri',
    type=click.STRING,
    default='http://localhost:3000/',
    required=False,
    help='redirect uri for application',
)
@click.option(
    '--clientid',
    type=click.STRING,
    default=CLIENT_ID,
    required=False,
    help='clientID used in the application',
)
@click.command()
def command(username, uri, clientid):
    if Application.objects.filter(client_id=clientid).exists():
        click.echo('The client already exists. You can administer it from the admin console.')
        return

    if username:
        user = User.objects.get(username=username)
    else:
        first_user = User.objects.first()
        if first_user:
            user = first_user

    if user:
        application = Application(
            name='batsai-client',
            client_id=clientid,
            client_secret='',
            client_type='public',
            redirect_uris=uri,
            authorization_grant_type='authorization-code',
            user=user,
            skip_authorization=True,
        )
        application.save()
