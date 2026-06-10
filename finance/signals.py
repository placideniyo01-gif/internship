from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Deposit, Withdrawal

from accounts.models import (
    Profile,
    Referral,
    ReferralDeposit
)


@receiver(post_save, sender=Deposit)
def credit_balance(sender, instance, **kwargs):

    if (
        instance.status == "Approved"
        and not instance.credited
    ):

        profile = Profile.objects.get(
            user=instance.user
        )

        profile.balance += instance.amount
        profile.total_deposit += instance.amount
        profile.save()

        try:

            referral = Referral.objects.get(
                referred_user=instance.user
            )

            first_deposit = Deposit.objects.filter(
                user=instance.user,
                status="Approved"
            ).count()

            if first_deposit == 1:

                if instance.amount < 100:
                    rate = 0.001

                elif instance.amount < 500:
                    rate = 0.002

                else:
                    rate = 0.003

                ReferralDeposit.objects.create(
                    referral=referral,
                    deposit_amount=instance.amount,
                    bonus_rate=rate
                )

        except Referral.DoesNotExist:
            pass

        instance.credited = True
        instance.save(
            update_fields=["credited"]
        )


@receiver(post_save, sender=Withdrawal)
def process_withdrawal(sender, instance, **kwargs):

    if (
        instance.status == "Approved"
        and not instance.processed
    ):

        profile = Profile.objects.get(
            user=instance.user
        )

        if profile.balance >= instance.amount:

            profile.balance -= instance.amount
            profile.save()

            instance.processed = True
            instance.save(
                update_fields=["processed"]
            )