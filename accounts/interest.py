
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from .models import Profile, InterestWallet


DAILY_INTEREST_RATE = Decimal("0.05")
SECONDS_PER_DAY = Decimal("86400")


def get_elapsed_seconds(start, end):
    """
    Calculate elapsed seconds accurately without float conversion.
    """
    difference = end - start

    return (
        Decimal(difference.days * 86400)
        + Decimal(difference.seconds)
        + Decimal(difference.microseconds) / Decimal("1000000")
    )


@transaction.atomic
def settle_interest(user, now=None):
    """
    Save interest earned using the user's balance
    during the elapsed period.

    Interest is calculated on the current balance,
    regardless of whether it came from a deposit,
    internal transfer, or another balance update.
    """

    if now is None:
        now = timezone.now()

    profile = Profile.objects.select_for_update().get(
        user=user
    )

    wallet, created = InterestWallet.objects.select_for_update().get_or_create(
        user=user
    )

    # Start interest tracking from the first settlement.
    # No interest is calculated for time before this point.
    if wallet.started_at is None:
        wallet.started_at = now
        wallet.last_update = now

        wallet.save(
            update_fields=[
                "started_at",
                "last_update"
            ]
        )

        return profile, wallet

    last_update = wallet.last_update or wallet.started_at

    if now <= last_update:
        return profile, wallet

    elapsed_seconds = get_elapsed_seconds(
        last_update,
        now
    )

    # Calculate interest using the balance that existed
    # during this elapsed period.
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
    """
    Display saved interest plus interest accumulated
    since the last settlement.
    """

    if now is None:
        now = timezone.now()

    current_interest = wallet.amount

    if wallet.started_at is None:
        return current_interest

    last_update = wallet.last_update or wallet.started_at

    if now <= last_update:
        return current_interest

    if profile.balance <= 0:
        return current_interest

    elapsed_seconds = get_elapsed_seconds(
        last_update,
        now
    )

    interest_per_second = (
        profile.balance * DAILY_INTEREST_RATE
    ) / SECONDS_PER_DAY

    current_interest += (
        interest_per_second * elapsed_seconds
    )

    return current_interest


def get_interest_per_second(profile, wallet=None):
    """
    Return the current interest earned per second
    based on the user's current balance.
    """

    if profile.balance <= 0:
        return Decimal("0")

    return (
        profile.balance * DAILY_INTEREST_RATE
    ) / SECONDS_PER_DAY
