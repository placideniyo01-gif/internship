from decimal import Decimal

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Deposit, Withdrawal

from accounts.models import (
    Profile,
    Referral,
    ReferralDeposit,
    InterestWallet
)

from accounts.interest import settle_interest


@receiver(post_save, sender=Deposit)
@transaction.atomic
def credit_balance(sender, instance, **kwargs):

    if instance.status != "Approved" or instance.credited:
        return

    now = timezone.now()

    profile, wallet = settle_interest(
        instance.user,
        now
    )

    # Add the newly approved deposit
    profile.balance += instance.amount
    profile.total_deposit += instance.amount

    profile.save(
        update_fields=[
            "balance",
            "total_deposit"
        ]
    )

    # Start interest after the first approved deposit
    if wallet.started_at is None:

        wallet.started_at = now
        wallet.last_update = now

        wallet.save(
            update_fields=[
                "started_at",
                "last_update"
            ]
        )

    # Referral bonus: first approved deposit only
    try:

        referral = Referral.objects.get(
            referred_user=instance.user
        )

        first_deposit = Deposit.objects.filter(
            user=instance.user,
            status="Approved",
            credited=True
        ).count()

        # Current deposit is not yet marked credited,
        # so count the already credited deposits.
        if first_deposit == 0:

            if instance.amount < Decimal("100"):
                rate = Decimal("0.001")

            elif instance.amount < Decimal("500"):
                rate = Decimal("0.002")

            else:
                rate = Decimal("0.003")

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
@transaction.atomic
def process_withdrawal(sender, instance, **kwargs):

    if instance.status != "Approved" or instance.processed:
        return

    now = timezone.now()

    profile, wallet = settle_interest(
        instance.user,
        now
    )

    if profile.balance >= instance.amount:

        profile.balance -= instance.amount

        profile.save(
            update_fields=["balance"]
        )

        instance.processed = True

        instance.save(
            update_fields=["processed"]
        )