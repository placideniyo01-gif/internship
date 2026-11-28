
from calendar import monthrange
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import Profile, InterestWallet


DAILY_INTEREST_RATE = Decimal("0.05")
SECONDS_PER_DAY = Decimal("86400")
ZERO = Decimal("0")


def add_calendar_months(value, months):
    """
    Add calendar months while preserving time and timezone.
    If the target month has fewer days, use its last day.
    """

    month_index = (
        value.year * 12
        + (value.month - 1)
        + months
    )

    year = month_index // 12
    month = (month_index % 12) + 1

    day = min(
        value.day,
        monthrange(year, month)[1]
    )

    return value.replace(
        year=year,
        month=month,
        day=day
    )


def get_elapsed_seconds(start, end):
    if not start or not end or end <= start:
        return ZERO

    return Decimal(
        str((end - start).total_seconds())
    )


@transaction.atomic
def settle_interest(user, now=None):
    """
    Calculate interest exclusively on blocked_amount.

    At unlock time:
    - Calculate interest up to the exact unlock time.
    - Move all blocked funds to available balance.
    - Keep earned interest in InterestWallet.
    """

    if now is None:
        now = timezone.now()

    # Lock the user's profile.
    profile = Profile.objects.select_for_update().get(
        user=user
    )

    # Get or create the interest wallet.
    wallet, created = InterestWallet.objects.get_or_create(
        user=user
    )

    # Lock the wallet before changing its amount.
    wallet = InterestWallet.objects.select_for_update().get(
        pk=wallet.pk
    )

    blocked_amount = profile.blocked_amount or ZERO

    # No blocked funds means no interest.
    if blocked_amount <= ZERO:

        # Clean up incomplete block information if necessary.
        fields_to_update = []

        if profile.blocked_amount != ZERO:
            profile.blocked_amount = ZERO
            fields_to_update.append("blocked_amount")

        if profile.block_started_at is not None:
            profile.block_started_at = None
            fields_to_update.append("block_started_at")

        if profile.block_unlock_at is not None:
            profile.block_unlock_at = None
            fields_to_update.append("block_unlock_at")

        if fields_to_update:
            profile.save(update_fields=fields_to_update)

        return profile, wallet

    block_started_at = profile.block_started_at
    unlock_at = profile.block_unlock_at

    # Protect records that have incomplete block dates.
    if not block_started_at:
        block_started_at = now
        profile.block_started_at = block_started_at

    if not unlock_at:
        unlock_at = add_calendar_months(
            block_started_at,
            3
        )
        profile.block_unlock_at = unlock_at

    # Interest must never start before the block started.
    interest_start = wallet.last_update or block_started_at

    if interest_start < block_started_at:
        interest_start = block_started_at

    # Never calculate interest beyond the unlock date.
    interest_end = min(now, unlock_at)

    # Calculate interest only for the elapsed period.
    if interest_end > interest_start:

        elapsed_seconds = get_elapsed_seconds(
            interest_start,
            interest_end
        )

        earned_interest = (
            blocked_amount
            * DAILY_INTEREST_RATE
            * elapsed_seconds
            / SECONDS_PER_DAY
        )

        wallet.amount = (
            wallet.amount or ZERO
        ) + earned_interest

    # Save the calculation time without moving it backwards.
    if wallet.last_update is None:
        wallet.last_update = interest_end
    else:
        wallet.last_update = max(
            wallet.last_update,
            interest_end
        )

    wallet.save(update_fields=[
        "amount",
        "last_update",
    ])

    # Save missing block dates if they were repaired.
    profile_fields = []

    if profile.block_started_at != block_started_at:
        profile.block_started_at = block_started_at
        profile_fields.append("block_started_at")

    if profile.block_unlock_at != unlock_at:
        profile.block_unlock_at = unlock_at
        profile_fields.append("block_unlock_at")

    # Unlock all blocked funds together at the original expiry.
    if now >= unlock_at:

        profile.balance = (
            profile.balance or ZERO
        ) + blocked_amount

        profile.blocked_amount = ZERO
        profile.block_started_at = None
        profile.block_unlock_at = None

        profile_fields.extend([
            "balance",
            "blocked_amount",
            "block_started_at",
            "block_unlock_at",
        ])

    if profile_fields:
        profile.save(
            update_fields=list(set(profile_fields))
        )

    return profile, wallet


def get_current_interest(profile, wallet, now=None):
    """
    Return stored interest plus projected interest
    up to the current time, capped at unlock time.
    """

    if now is None:
        now = timezone.now()

    current_interest = wallet.amount or ZERO
    blocked_amount = profile.blocked_amount or ZERO

    if blocked_amount <= ZERO:
        return current_interest

    if not profile.block_started_at:
        return current_interest

    if not profile.block_unlock_at:
        return current_interest

    interest_start = (
        wallet.last_update
        or profile.block_started_at
    )

    if interest_start < profile.block_started_at:
        interest_start = profile.block_started_at

    interest_end = min(
        now,
        profile.block_unlock_at
    )

    elapsed_seconds = get_elapsed_seconds(
        interest_start,
        interest_end
    )

    if elapsed_seconds <= ZERO:
        return current_interest

    projected_interest = (
        blocked_amount
        * DAILY_INTEREST_RATE
        * elapsed_seconds
        / SECONDS_PER_DAY
    )

    return current_interest + projected_interest


def get_interest_per_second(profile, wallet=None):
    """
    Calculate live interest per second using blocked funds only.
    """

    blocked_amount = profile.blocked_amount or ZERO

    if blocked_amount <= ZERO:
        return ZERO

    if not profile.block_unlock_at:
        return ZERO

    if timezone.now() >= profile.block_unlock_at:
        return ZERO

    return (
        blocked_amount
        * DAILY_INTEREST_RATE
        / SECONDS_PER_DAY
    )
