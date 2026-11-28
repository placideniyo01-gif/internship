
from decimal import Decimal, InvalidOperation
from datetime import timedelta

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import (
    update_session_auth_hash,
    logout,
)
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

import json

from finance.models import InternshipTransfer
from support.models import SupportMessage

from accounts.interest import (
    settle_interest,
    get_current_interest,
    get_interest_per_second,
    add_calendar_months,
)

from accounts.models import (
    Profile,
    InterestWallet,
    Referral,
    ReferralDeposit,
)


ZERO = Decimal("0")


@login_required
def dashboard(request):

    profile, wallet = settle_interest(
        request.user,
        timezone.now()
    )

    now = timezone.now()

    current_interest = get_current_interest(
        profile,
        wallet,
        now
    )

    interest_per_second = get_interest_per_second(
        profile,
        wallet
    )

    # Interest claim cooldown: 7 days
    next_claim_at = None
    can_claim_interest = True

    if wallet.last_claim_at:

        next_claim_at = (
            wallet.last_claim_at + timedelta(days=7)
        )

        if now < next_claim_at:
            can_claim_interest = False

    if current_interest <= ZERO:
        can_claim_interest = False

    # ======================
    # REFERRALS
    # ======================

    referrals_qs = Referral.objects.filter(
        referrer=request.user
    )

    referrals_count = referrals_qs.count()

    for member in referrals_qs:

        deposit = ReferralDeposit.objects.filter(
            referral=member
        ).first()

        if deposit:
            member.referral_bonus = (
                deposit.bonus_rate * 100
            )
        else:
            member.referral_bonus = ZERO

    active_bonus = ZERO
    locked_bonus = ZERO
    referral_profit = ZERO
    total_bonus_rate = ZERO

    deposits = ReferralDeposit.objects.filter(
        referral__referrer=request.user
    )

    for d in deposits:

        elapsed_seconds = (
            now - d.started_at
        ).total_seconds()

        hours = elapsed_seconds / 3600

        days = Decimal(
            str(elapsed_seconds / 86400)
        )

        if days > 90:
            continue

        total_bonus_generated = (
            d.deposit_amount
            * d.bonus_rate
            * days
        )

        referral_profit += total_bonus_generated

        available_bonus = (
            total_bonus_generated
            - d.claimed_bonus
        )

        if available_bonus < ZERO:
            available_bonus = ZERO

        if hours >= 1:
            active_bonus += available_bonus
        else:
            locked_bonus += available_bonus

        total_bonus_rate += (
            d.bonus_rate * 100
        )

    referral_link = request.build_absolute_uri(
        f"/signup/?ref={profile.referral_code}"
    )

    unread_support = SupportMessage.objects.filter(
        receiver=request.user,
        seen=False
    ).count()

    unread_sent_transfers = InternshipTransfer.objects.filter(
        user=request.user,
        receiver__isnull=False,
        status="SUCCESS",
        seen_by_sender=False
    ).select_related(
        "receiver"
    ).order_by("-created_at")

    unread_received_transfers = InternshipTransfer.objects.filter(
        receiver=request.user,
        status="SUCCESS",
        seen_by_receiver=False
    ).select_related(
        "user"
    ).order_by("-created_at")

    context = {

        "username": request.user.username,

        # Available balance
        "balance": round(profile.balance, 8),

        # Blocked balance
        "blocked_amount": round(
            profile.blocked_amount,
            8
        ),

        "block_started_at": profile.block_started_at,

        "block_unlock_at": profile.block_unlock_at,

        "has_active_block": (
            profile.blocked_amount > ZERO
            and profile.block_unlock_at is not None
        ),

        # Interest earned on blocked amount only
        "interest": round(current_interest, 8),

        "interest_rate_per_second": float(
            interest_per_second
        ),

        "can_claim_interest": can_claim_interest,

        "next_claim_at": next_claim_at,

        "referrals": referrals_count,

        "active_bonus": round(active_bonus, 6),

        "unread_sent_transfers": unread_sent_transfers,

        "unread_received_transfers": unread_received_transfers,

        "locked_bonus": round(locked_bonus, 6),

        "referral_profit": round(referral_profit, 6),

        "daily_ref_bonus_percent": round(
            total_bonus_rate,
            2
        ),

        "team": referrals_qs,

        "referral_code": profile.referral_code,

        "referral_link": referral_link,

        "unread_support": unread_support,
    }

    return render(
        request,
        "dashboard/dashboard.html",
        context
    )


# ==========================================
# BLOCK AMOUNT FOR 3 MONTHS
# ==========================================

@login_required
@require_POST
@transaction.atomic
def block_amount(request):

    amount_input = request.POST.get(
        "amount",
        ""
    ).strip()

    try:

        amount = Decimal(amount_input)

        if (
            not amount.is_finite()
            or amount <= ZERO
            or amount.as_tuple().exponent < -8
        ):
            raise InvalidOperation

    except (InvalidOperation, ValueError):

        messages.error(
            request,
            "Please enter a valid amount."
        )

        return redirect("dashboard")

    now = timezone.now()

    # Settle any previous interest and unlock an expired block first.
    settle_interest(
        request.user,
        now
    )

    # Lock the profile before moving funds.
    profile = Profile.objects.select_for_update().get(
        user=request.user
    )

    if amount > profile.balance:

        messages.error(
            request,
            "Insufficient Available Balance."
        )

        return redirect("dashboard")

    # Get and lock the interest wallet.
    wallet, created = InterestWallet.objects.get_or_create(
        user=request.user
    )

    wallet = InterestWallet.objects.select_for_update().get(
        pk=wallet.pk
    )

    # If there is no active block, start a new 3-month period.
    if (
        profile.blocked_amount <= ZERO
        or not profile.block_unlock_at
    ):

        profile.block_started_at = now

        profile.block_unlock_at = add_calendar_months(
            now,
            3
        )

        profile.blocked_amount = ZERO

    # Move money from Available Balance to Blocked Amount.
    profile.balance -= amount
    profile.blocked_amount += amount

    profile.save(update_fields=[
        "balance",
        "blocked_amount",
        "block_started_at",
        "block_unlock_at",
    ])

    # Important:
    # Start calculating interest on the new total blocked amount
    # from this exact moment. Do not reset the original unlock date
    # when adding more money to an existing block.
    wallet.last_update = now

    wallet.save(update_fields=[
        "last_update"
    ])

    messages.success(
        request,
        (
            f"{amount:.8f} USDT has been blocked successfully. "
            f"Your blocked funds will unlock on "
            f"{timezone.localtime(profile.block_unlock_at).strftime('%d %B %Y %H:%M')}."
        )
    )

    return redirect("dashboard")


# ==========================================
# CLAIM REFERRAL BONUS
# ==========================================


@login_required
@transaction.atomic
def claim_bonus(request):

    now = timezone.now()

    profile, wallet = settle_interest(
        request.user,
        now
    )

    total_claim = ZERO

    deposits = (
        ReferralDeposit.objects
        .select_for_update()
        .filter(referral__referrer=request.user)
        .order_by("pk")
    )

    for d in deposits:

        elapsed_seconds = (
            now - d.started_at
        ).total_seconds()

        days = Decimal(
            str(elapsed_seconds / 86400)
        )

        if days < Decimal("30") or days > Decimal("90"):
            continue

        total_bonus_generated = (
            d.deposit_amount
            * d.bonus_rate
            * days
        )

        available_bonus = (
            total_bonus_generated - d.claimed_bonus
        )

        if available_bonus <= ZERO:
            continue

        total_claim += available_bonus

        d.claimed_bonus += available_bonus

        d.save(
            update_fields=["claimed_bonus"]
        )

    if total_claim > ZERO:

        profile.balance += total_claim
        profile.total_earned += total_claim

        profile.save(
            update_fields=[
                "balance",
                "total_earned",
            ]
        )

        messages.success(
            request,
            "Referral bonus claimed successfully."
        )

    else:

        messages.info(
            request,
            "No referral bonus is currently available to claim."
        )

    return redirect("dashboard")



# ==========================================
# CLAIM INTEREST
# ==========================================

@login_required
@require_POST
@transaction.atomic
def claim_interest(request):

    now = timezone.now()

    profile, wallet = settle_interest(
        request.user,
        now
    )

    # Check the 7-day claim period.
    if wallet.last_claim_at:

        next_claim_at = (
            wallet.last_claim_at + timedelta(days=7)
        )

        if now < next_claim_at:

            remaining_seconds = int(
                (next_claim_at - now).total_seconds()
            )

            days, remainder = divmod(
                remaining_seconds,
                86400
            )

            hours, remainder = divmod(
                remainder,
                3600
            )

            minutes, seconds = divmod(
                remainder,
                60
            )

            messages.error(
                request,
                (
                    f"You can claim interest again in "
                    f"{days} days, {hours} hours, "
                    f"{minutes} minutes and {seconds} seconds."
                )
            )

            return redirect("dashboard")

    total_interest = wallet.amount or ZERO

    if total_interest <= ZERO:

        messages.error(
            request,
            "You do not have interest available to claim yet."
        )

        return redirect("dashboard")

    # Interest is credited to Available Balance.
    # Available Balance does not earn interest automatically.
    profile.balance += total_interest
    profile.total_earned += total_interest

    profile.save(update_fields=[
        "balance",
        "total_earned",
    ])

    wallet.amount = ZERO
    wallet.last_update = now
    wallet.last_claim_at = now

    wallet.save(update_fields=[
        "amount",
        "last_update",
        "last_claim_at",
    ])

    messages.success(
        request,
        (
            "Interest claimed successfully! "
            "It has been added to your Available Balance. "
            "To earn interest on it, you can block it again."
        )
    )

    return redirect("dashboard")


# ==========================================
# LIVE DASHBOARD DATA
# ==========================================

@login_required
def live_balance(request):

    profile, wallet = settle_interest(
        request.user,
        timezone.now()
    )

    now = timezone.now()

    current_interest = get_current_interest(
        profile,
        wallet,
        now
    )

    interest_per_second = get_interest_per_second(
        profile,
        wallet
    )

    active_bonus = ZERO
    locked_bonus = ZERO
    referral_profit = ZERO

    deposits = ReferralDeposit.objects.filter(
        referral__referrer=request.user
    )

    for d in deposits:

        elapsed_seconds = (
            now - d.started_at
        ).total_seconds()

        days = Decimal(
            str(elapsed_seconds / 86400)
        )

        total_bonus_generated = (
            d.deposit_amount
            * d.bonus_rate
            * min(days, Decimal("90"))
        )

        referral_profit += total_bonus_generated

        available_bonus = max(
            total_bonus_generated - d.claimed_bonus,
            ZERO
        )

        if days >= 30:
            active_bonus += available_bonus
        else:
            locked_bonus += available_bonus

    return JsonResponse({

        "balance": float(profile.balance),

        "blocked_amount": float(
            profile.blocked_amount
        ),

        "block_started_at": (
            profile.block_started_at.isoformat()
            if profile.block_started_at
            else None
        ),

        "block_unlock_at": (
            profile.block_unlock_at.isoformat()
            if profile.block_unlock_at
            else None
        ),

        "interest": float(current_interest),

        "interest_rate_per_second": float(
            interest_per_second
        ),

        "active_bonus": float(active_bonus),

        "locked_bonus": float(locked_bonus),

        "referral_profit": float(referral_profit),

    })


# ==========================================
# WELCOME
# ==========================================

@login_required
def welcome(request):

    return render(
        request,
        "dashboard/welcome.html"
    )


# ==========================================
# SETTINGS
# ==========================================

@login_required
def settings_view(request):

    return render(
        request,
        "dashboard/settings.html"
    )


# ==========================================
# CHANGE PASSWORD
# ==========================================

@login_required
def change_password(request):

    if request.method == "POST":

        current_password = request.POST.get(
            "current_password",
            ""
        )

        new_password = request.POST.get(
            "new_password",
            ""
        )

        confirm_password = request.POST.get(
            "confirm_password",
            ""
        )

        if not request.user.check_password(current_password):

            messages.error(
                request,
                "Current password is incorrect."
            )

            return redirect("change_password")

        if new_password != confirm_password:

            messages.error(
                request,
                "New passwords do not match."
            )

            return redirect("change_password")

        if current_password == new_password:

            messages.error(
                request,
                "New password must be different."
            )

            return redirect("change_password")

        try:

            validate_password(
                new_password,
                request.user
            )

        except ValidationError as error:

            for message in error.messages:
                messages.error(request, message)

            return redirect("change_password")

        request.user.set_password(new_password)
        request.user.save()

        update_session_auth_hash(
            request,
            request.user
        )

        messages.success(
            request,
            "Password changed successfully!"
        )

        return redirect("settings")

    return render(
        request,
        "dashboard/change_password.html"
    )


# ==========================================
# DELETE ACCOUNT
# ==========================================

@login_required
def delete_account(request):

    if request.method == "POST":

        profile, wallet = settle_interest(
            request.user,
            timezone.now()
        )

        if (
            profile.balance > ZERO
            or profile.blocked_amount > ZERO
            or (wallet.amount or ZERO) > ZERO
        ):

            messages.error(
                request,
                (
                    "Your account cannot be deleted while "
                    "you have available balance, blocked funds "
                    "or unclaimed interest."
                )
            )

            return redirect("settings")

        user = request.user

        logout(request)

        user.delete()

        messages.success(
            request,
            "Account deleted successfully."
        )

        return redirect("login")

    return redirect("settings")


# ==========================================
# SUPPORT NOTIFICATIONS
# ==========================================

@login_required
def unread_support_count(request):

    count = SupportMessage.objects.filter(
        receiver=request.user,
        seen=False
    ).count()

    return JsonResponse({
        "count": count
    })


# ==========================================
# USERNAME API
# ==========================================

@csrf_exempt
def check_username_api(request):

    try:

        data = json.loads(
            request.body
        )

    except Exception:

        return JsonResponse({
            "success": False,
            "message": "Invalid request."
        }, status=400)

    if data.get("secret_key") != settings.USDT_API_SECRET:

        return JsonResponse({
            "success": False,
            "message": "Unauthorized."
        }, status=403)

    username = data.get(
        "username"
    )

    user = User.objects.filter(
        username=username
    ).first()

    if not user:

        return JsonResponse({
            "success": False,
            "message": "Username not found."
        })

    return JsonResponse({

        "success": True,

        "username": user.username,

        "names": user.get_full_name() or user.username

    })


# ==========================================
# INTERNAL TRANSFER
# ==========================================

@login_required
def internal_transfer(request):

    if request.method == "POST":

        # Ensure any due block has been unlocked.
        settle_interest(
            request.user,
            timezone.now()
        )

        username = request.POST.get(
            "username",
            ""
        ).strip()

        amount_input = request.POST.get(
            "amount",
            ""
        ).strip()

        if not username:

            messages.error(
                request,
                "Please enter the recipient username."
            )

            return redirect("internal_transfer")

        receiver = User.objects.filter(
            username__iexact=username,
            is_active=True
        ).first()

        if not receiver:

            messages.error(
                request,
                "User not found. Please check the username and try again."
            )

            return redirect("internal_transfer")

        if receiver.pk == request.user.pk:

            messages.error(
                request,
                "You cannot transfer money to yourself."
            )

            return redirect("internal_transfer")

        try:

            amount = Decimal(amount_input)

            if (
                not amount.is_finite()
                or amount <= ZERO
                or amount.as_tuple().exponent < -2
            ):
                raise InvalidOperation

        except (InvalidOperation, ValueError):

            messages.error(
                request,
                "Please enter a valid amount with a maximum of 2 decimal places."
            )

            return redirect("internal_transfer")

        profile = Profile.objects.get(
            user=request.user
        )

        # Only Available Balance can be transferred.
        if amount > profile.balance:

            messages.error(
                request,
                "Insufficient Available Balance."
            )

            return redirect("internal_transfer")

        request.session["pending_internal_transfer"] = {

            "receiver_id": receiver.pk,

            "receiver_username": receiver.username,

            "amount": str(amount),

        }

        request.session.set_expiry(600)

        return render(
            request,
            "dashboard/transfer_confirm.html",
            {
                "receiver": receiver,
                "amount": amount,
            }
        )

    return render(
        request,
        "dashboard/internal_transfer.html"
    )



@login_required
@require_POST
def confirm_internal_transfer(request):

    pending = request.session.get(
        "pending_internal_transfer"
    )

    if not pending:

        messages.error(
            request,
            "Transfer session expired. Please try again."
        )

        return redirect("internal_transfer")

    password = request.POST.get("password", "")

    if not check_password(
        password,
        request.user.password
    ):

        messages.error(
            request,
            "Incorrect password. Transfer was not completed."
        )

        return redirect("internal_transfer")

    try:

        receiver = User.objects.get(
            pk=pending["receiver_id"],
            username=pending["receiver_username"],
            is_active=True
        )

        amount = Decimal(
            pending["amount"]
        )

        if (
            receiver.pk == request.user.pk
            or not amount.is_finite()
            or amount <= ZERO
            or amount != amount.quantize(Decimal("0.01"))
        ):
            raise ValueError

        with transaction.atomic():

            # Settle both accounts in a consistent order.
            users = sorted(
                [request.user, receiver],
                key=lambda user: user.pk
            )

            for account_user in users:

                settle_interest(
                    account_user,
                    timezone.now()
                )

            # Lock both profiles.
            profiles = {
                profile.user_id: profile
                for profile in (
                    Profile.objects.select_for_update()
                    .filter(user__in=users)
                    .order_by("user_id")
                )
            }

            sender_profile = profiles[
                request.user.pk
            ]

            receiver_profile = profiles[
                receiver.pk
            ]

            # Available Balance only.
            if sender_profile.balance < amount:

                raise ValueError(
                    "Insufficient Available Balance."
                )

            sender_profile.balance -= amount
            receiver_profile.balance += amount

            sender_profile.save(
                update_fields=["balance"]
            )

            receiver_profile.save(
                update_fields=["balance"]
            )

            # Save transaction history inside the same atomic block.
            InternshipTransfer.objects.create(
                user=request.user,
                receiver=receiver,
                receiver_username=receiver.username,
                amount=amount,
                status="SUCCESS",
                seen_by_sender=False,
                seen_by_receiver=False
            )

        # Clear session only after the transaction succeeds.
        request.session.pop(
            "pending_internal_transfer",
            None
        )

        messages.success(
            request,
            (
                f"Successfully sent {amount:.2f} USDT "
                f"to {receiver.username}."
            )
        )

        return redirect("dashboard")

    except User.DoesNotExist:

        request.session.pop(
            "pending_internal_transfer",
            None
        )

        messages.error(
            request,
            "Recipient account no longer exists."
        )

    except (ValueError, KeyError, InvalidOperation):

        messages.error(
            request,
            "Transfer could not be completed. Please check your balance and try again."
        )

    except Exception:

        logger.exception(
            "Internal transfer failed."
        )

        messages.error(
            request,
            "An unexpected error occurred. Please try again."
        )

    return redirect("internal_transfer")
