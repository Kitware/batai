from django.contrib.auth.models import User
from django.db.models.signals import post_save
import factory.django

from bats_ai.core.models import UserProfile, VettingDetails


@factory.django.mute_signals(post_save)
class UserFactory(factory.django.DjangoModelFactory[User]):
    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.SelfAttribute('email')
    email = factory.Faker('safe_email')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')

    profile = factory.RelatedFactory(
        'bats_ai.core.tests.factories.ProfileFactory', factory_related_name='user'
    )

    # flake8 complains that the first argument to this function is not "self," but this is not
    # a class method, this is a post-generation hook
    @factory.post_generation
    def save_after_generation(instance: User, create: bool, extracted, **kwargs):  # noqa: N805
        if create:
            instance.save()


class SuperuserFactory(UserFactory):
    is_superuser = True
    is_staff = True


@factory.django.mute_signals(post_save)
class ProfileFactory(factory.django.DjangoModelFactory[UserProfile]):
    class Meta:
        model = UserProfile

    verified = True
    user = factory.SubFactory(UserFactory, profile=None)


class VettingDetailsFactory(factory.django.DjangoModelFactory[VettingDetails]):

    class Meta:
        model = VettingDetails

    user = factory.SubFactory(UserFactory)
    reference_materials = factory.Faker('paragraph', nb_sentences=3)
