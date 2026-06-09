import uuid

from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver

from .models import (
    Profile,
    InterestWallet
)


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):

    if created:

        Profile.objects.create(
            user=instance,
            referral_code=str(uuid.uuid4())[:8].upper()
        )

        InterestWallet.objects.create(
            user=instance
        )