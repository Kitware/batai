from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone
import factory.django
from oauth2_provider.models import AccessToken

from bats_ai.core.models import VettingDetails


class UserFactory(factory.django.DjangoModelFactory[User]):
    class Meta:
        model = User

    username = factory.SelfAttribute('email')
    email = factory.Faker('safe_email')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')


class SuperuserFactory(factory.django.DjangoModelFactory[User]):
    class Meta:
        model = User
        django_get_or_create = ('email',)

    username = factory.SelfAttribute('email')
    email = factory.Faker('safe_email')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    is_superuser = True
    is_staff = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        manager = cls._get_manager(model_class)
        return manager.create_superuser(*args, **kwargs)


class VettingDetailsFactory(factory.django.DjangoModelFactory[VettingDetails]):

    class Meta:
        model = VettingDetails

    user = factory.SubFactory(UserFactory)
    reference_materials = factory.Faker('paragraph', nb_sentences=3)


class AccessTokenFactory(factory.django.DjangoModelFactory[AccessToken]):
    class Meta:
        model = AccessToken

    user = factory.SubFactory(UserFactory)
    token = factory.Faker('uuid4')
    scope = 'read write'
    expires = factory.LazyFunction(lambda: timezone.now() + timedelta(hours=1))
