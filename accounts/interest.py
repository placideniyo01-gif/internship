from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from .models import Profile, InterestWallet


DAILY_INTEREST_RATE = Decimal("0.05")
SECONDS_PER_DAY = Decimal("86400")


@transaction.atomic
def settle_interest(user, now=None):

    if now is None:
        now = timezone.now()

    profile = Profile.objects.select_for_update().get(
        user=user
    )

    wallet, created = InterestWallet.objects.select_for_update().get_or_create(
        user=user
    )

    # Interest has not started yet
    if wallet.started_at is None:
        return profile, wallet

    last_update = wallet.last_update or wallet.started_at

    if now <= last_update:
        return profile, wallet

    elapsed_seconds = Decimal(
        str((now - last_update).total_seconds())
    )

    if elapsed_seconds > 0 and profile.balance > 0:

        interest_per_second = (
            profile.balance * DAILY_INTEREST_RATE
        ) / SECONDS_PER_DAY

        newly_earned = (
            interest_per_second * elapsed_seconds
        )

        wallet.amount += newly_earned

    wallet.last_update = now

    wallet.save(
        update_fields=[
            "amount",
            "last_update"
        ]
    )

    return profile, wallet


def get_current_interest(profile, wallet, now=None):

    if now is None:
        now = timezone.now()

    current_interest = wallet.amount

    if wallet.started_at is None:
        return current_interest

    last_update = wallet.last_update or wallet.started_at

    if now > last_update and profile.balance > 0:

        elapsed_seconds = Decimal(
            str((now - last_update).total_seconds())
        )

        interest_per_second = (
            profile.balance * DAILY_INTEREST_RATE
        ) / SECONDS_PER_DAY

        current_interest += (
            interest_per_second * elapsed_seconds
        )

    return current_interest


def get_interest_per_second(profile, wallet):

    if wallet.started_at is None:
        return Decimal("0")

    if profile.balance <= 0:
        return Decimal("0")

    return (
        profile.balance * DAILY_INTEREST_RATE
    ) / SECONDS_PER_DAY