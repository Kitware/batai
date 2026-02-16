from django.contrib.auth.models import User
import factory.django

from bats_ai.core.models import VettingDetails


class UserFactory(factory.django.DjangoModelFactory[User]):
    class Meta:
        model = User

    username = factory.SelfAttribute('email')
    email = factory.Faker('safe_email')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')


class SuperuserFactory(UserFactory):
    is_superuser = True
    is_staff = True


class VettingDetailsFactory(factory.django.DjangoModelFactory[VettingDetails]):
    class Meta:
        model = VettingDetails

    user = factory.SubFactory(UserFactory)
    reference_materials = factory.Faker('paragraph', nb_sentences=3)
