
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
)

from accounts.interest import settle_interest


# =====================================================
# DEPOSIT SIGNAL
# Credits Available Balance only.
# Creates referral deposit on first approved deposit.
# Processes each deposit only once.
# =====================================================

@receiver(post_save, sender=Deposit)
@transaction.atomic
def credit_balance(sender, instance, **kwargs):

    # Lock the deposit row to prevent duplicate processing.
    try:
        deposit = Deposit.objects.select_for_update().get(
            pk=instance.pk
        )
    except Deposit.DoesNotExist:
        return

    if deposit.status != "Approved" or deposit.credited:
        return

    now = timezone.now()

    # Settle any pending interest and unlock expired funds.
    profile, wallet = settle_interest(
        deposit.user,
        now
    )

    # Add deposit to Available Balance only.
    profile.balance = (
        profile.balance or Decimal("0")
    ) + deposit.amount

    profile.total_deposit = (
        profile.total_deposit or Decimal("0")
    ) + deposit.amount

    profile.save(
        update_fields=[
            "balance",
            "total_deposit",
        ]
    )

    # Referral bonus: first approved deposit only.
    # Profile locking inside settle_interest prevents
    # concurrent deposits from both being treated as first.
    already_credited = Deposit.objects.filter(
        user=deposit.user,
        status="Approved",
        credited=True
    ).exclude(
        pk=deposit.pk
    ).exists()

    if not already_credited:

        referral = Referral.objects.filter(
            referred_user=deposit.user
        ).first()

        if referral:

            # Prevent duplicate ReferralDeposit records.
            referral_deposit_exists = ReferralDeposit.objects.filter(
                referral=referral
            ).exists()

            if not referral_deposit_exists:

                if deposit.amount < Decimal("100"):
                    rate = Decimal("0.001")

                elif deposit.amount < Decimal("500"):
                    rate = Decimal("0.002")

                else:
                    rate = Decimal("0.003")

                ReferralDeposit.objects.create(
                    referral=referral,
                    deposit_amount=deposit.amount,
                    bonus_rate=rate
                )

    # Mark this deposit as credited.
    deposit.credited = True

    deposit.save(
        update_fields=["credited"]
    )

    # Keep the signal instance synchronized.
    instance.credited = True


# =====================================================
# WITHDRAWAL SIGNAL
# Deducts Available Balance only.
# Never deducts blocked_amount.
# Processes each withdrawal only once.
# =====================================================

@receiver(post_save, sender=Withdrawal)
@transaction.atomic
def process_withdrawal(sender, instance, **kwargs):

    # Lock the withdrawal row to prevent duplicate processing.
    try:
        withdrawal = Withdrawal.objects.select_for_update().get(
            pk=instance.pk
        )
    except Withdrawal.DoesNotExist:
        return

    if withdrawal.status != "Approved" or withdrawal.processed:
        return

    now = timezone.now()

    # Settle interest and unlock expired blocked funds.
    profile, wallet = settle_interest(
        withdrawal.user,
        now
    )

    available_balance = (
        profile.balance or Decimal("0")
    )

    # Withdraw from Available Balance only.
    if available_balance >= withdrawal.amount:

        profile.balance = (
            available_balance - withdrawal.amount
        )

        profile.save(
            update_fields=["balance"]
        )

        withdrawal.processed = True

        withdrawal.save(
            update_fields=["processed"]
        )

        instance.processed = True

    else:

        # Insufficient available balance:
        # return the request to Pending.
        withdrawal.status = "Pending"

        withdrawal.save(
            update_fields=["status"]
        )

        instance.status = "Pending"
