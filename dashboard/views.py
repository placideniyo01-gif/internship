from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
from decimal import Decimal
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import update_session_auth_hash
from datetime import timedelta
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from decimal import Decimal, InvalidOperation
from finance.models import InternshipTransfer
from accounts.interest import (
    settle_interest,
    get_current_interest,
    get_interest_per_second
)
from django.contrib import messages
from support.models import SupportMessage
from accounts.models import (
    Profile,
    InterestWallet,
    Referral,
    ReferralDeposit
)
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
import json
from django.conf import settings

@login_required
def dashboard(request):

    # Start or update interest calculation using the current balance.
    settle_interest(request.user, timezone.now())

    profile = Profile.objects.get(
        user=request.user
    )

    wallet, created = InterestWallet.objects.get_or_create(
        user=request.user
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

    if current_interest <= 0:
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
            member.referral_bonus = Decimal("0")

    active_bonus = Decimal("0")
    locked_bonus = Decimal("0")
    referral_profit = Decimal("0")
    total_bonus_rate = Decimal("0")

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
            d.deposit_amount *
            d.bonus_rate *
            days
        )

        referral_profit += total_bonus_generated

        available_bonus = (
            total_bonus_generated -
            d.claimed_bonus
        )

        if available_bonus < 0:
            available_bonus = Decimal("0")

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
    ).select_related("receiver").order_by("-created_at")

    unread_received_transfers = InternshipTransfer.objects.filter(
        receiver=request.user,
        status="SUCCESS",
        seen_by_receiver=False
    ).select_related("user").order_by("-created_at")

    context = {

        "username": request.user.username,

        "balance": round(profile.balance, 8),

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
            total_bonus_rate, 2
        ),

        "team": referrals_qs,

        "referral_code": profile.referral_code,

        "referral_link": referral_link,

        "unread_support": unread_support
    }

    return render(
        request,
        "dashboard/dashboard.html",
        context
    )

@login_required
@transaction.atomic
def claim_bonus(request):

    profile, wallet = settle_interest(
        request.user,
        timezone.now()
    )

    now = timezone.now()

    total_claim = Decimal("0")

    deposits = ReferralDeposit.objects.filter(
        referral__referrer=request.user
    )

    for d in deposits:

        hours = (
            now - d.started_at
        ).total_seconds() / 3600

        days = Decimal(
            str(
                (
                    now - d.started_at
                ).total_seconds() / 86400
            )
        )

        if days > 90:
            continue

        if days < 30:
            continue

        total_bonus_generated = (
            d.deposit_amount *
            d.bonus_rate *
            days
        )

        available_bonus = (
            total_bonus_generated -
            d.claimed_bonus
        )

        if available_bonus <= 0:
            continue

        total_claim += available_bonus

        d.claimed_bonus += available_bonus
        d.save()

    if total_claim > 0:

        profile.balance += total_claim
        profile.total_earned += total_claim
        profile.save()

    return redirect(
        "dashboard"
    )



@login_required
@require_POST
@transaction.atomic
def claim_interest(request):

    now = timezone.now()

    profile, wallet = settle_interest(
        request.user,
        now
    )

    # Check the 7-day claim period
    if wallet.last_claim_at:
        next_claim_at = (
            wallet.last_claim_at + timedelta(days=7)
        )

        if now < next_claim_at:
            remaining_seconds = int(
                (next_claim_at - now).total_seconds()
            )

            days, remainder = divmod(remaining_seconds, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)

            messages.error(
                request,
                (
                    f"You can claim interest again in "
                    f"{days} days, {hours} hours, "
                    f"{minutes} minutes and {seconds} seconds."
                )
            )

            return redirect("dashboard")

    total_interest = wallet.amount

    if total_interest <= 0:
        messages.error(
            request,
            "You do not have interest available to claim yet."
        )
        return redirect("dashboard")

    profile.balance += total_interest
    profile.total_earned += total_interest

    profile.save(update_fields=[
        "balance",
        "total_earned"
    ])

    wallet.amount = Decimal("0")
    wallet.last_update = now
    wallet.last_claim_at = now

    wallet.save(update_fields=[
        "amount",
        "last_update",
        "last_claim_at"
    ])

    messages.success(
        request,
        "Interest claimed successfully! Your new balance is now earning interest."
    )

    return redirect("dashboard")



@login_required
def live_balance(request):
    settle_interest(request.user, timezone.now())

    profile = Profile.objects.get(
        user=request.user
    )
    wallet, created = InterestWallet.objects.get_or_create(
        user=request.user
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

    active_bonus = Decimal("0")
    locked_bonus = Decimal("0")
    referral_profit = Decimal("0")

    deposits = ReferralDeposit.objects.filter(
        referral__referrer=request.user
    )

    for d in deposits:
        elapsed_seconds = (
            now - d.started_at
        ).total_seconds()

        days = Decimal(str(elapsed_seconds / 86400))

        total_bonus_generated = (
            d.deposit_amount * d.bonus_rate * min(days, Decimal("90"))
        )

        referral_profit += total_bonus_generated

        available_bonus = max(
            total_bonus_generated - d.claimed_bonus,
            Decimal("0")
        )

        if days >= 30:
            active_bonus += available_bonus
        else:
            locked_bonus += available_bonus

    return JsonResponse({
        "balance": float(profile.balance),
        "interest": float(current_interest),
        "interest_rate_per_second": float(interest_per_second),
        "active_bonus": float(active_bonus),
        "locked_bonus": float(locked_bonus),
        "referral_profit": float(referral_profit),
    })



@login_required
def welcome(request):

    return render(
        request,
        "dashboard/welcome.html"
    )

@login_required
def settings_view(request):

    return render(
        request,
        "dashboard/settings.html"
    )

from django.contrib.auth.hashers import check_password
import random


@login_required
def change_password(request):

    if request.method == "POST":

        current_password = request.POST.get("current_password", "")
        new_password = request.POST.get("new_password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not request.user.check_password(current_password):
            messages.error(request, "Current password is incorrect.")
            return redirect("change_password")

        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return redirect("change_password")

        if current_password == new_password:
            messages.error(request, "New password must be different.")
            return redirect("change_password")

        try:
            validate_password(new_password, request.user)

        except ValidationError as error:
            for message in error.messages:
                messages.error(request, message)

            return redirect("change_password")

        # Save the new password securely in the database
        request.user.set_password(new_password)
        request.user.save()

        # Keep the user logged in
        update_session_auth_hash(request, request.user)

        messages.success(
            request,
            "Password changed successfully!"
        )

        return redirect("settings")

    return render(
        request,
        "dashboard/change_password.html"
    )


from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


@login_required
def delete_account(request):

    if request.method == "POST":

        profile = request.user.profile

        if profile.balance > 0:

            messages.error(
                request,
                "Account with balance cannot be deleted."
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

from django.contrib.auth.decorators import login_required



@login_required
def unread_support_count(request):

    count = SupportMessage.objects.filter(
        receiver=request.user,
        seen=False
    ).count()

    return JsonResponse({
        "count": count
    })

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

@login_required
def internal_transfer(request):

    if request.method == "POST":

        username = request.POST.get("username", "").strip()
        amount_input = request.POST.get("amount", "").strip()

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

            if not amount.is_finite() or amount <= 0:
                raise InvalidOperation

            if amount.as_tuple().exponent < -2:
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

        if amount > profile.balance:
            messages.error(
                request,
                "Insufficient balance."
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
        messages.error(request, "Transfer session expired. Please try again.")
        return redirect("internal_transfer")

    password = request.POST.get("password", "")

    if not check_password(password, request.user.password):
        messages.error(request, "Incorrect password. Transfer was not completed.")
        return redirect("internal_transfer")

    try:
        receiver = User.objects.get(
            pk=pending["receiver_id"],
            username=pending["receiver_username"],
            is_active=True
        )

        amount = Decimal(pending["amount"])

        if receiver.pk == request.user.pk or amount <= 0:
            raise ValueError

        with transaction.atomic():

            # Settle interest for both accounts before changing balances.
            # Lock users in a consistent order.
            users = sorted(
                [request.user, receiver],
                key=lambda user: user.pk
            )

            for account_user in users:
                settle_interest(account_user, timezone.now())

            # Lock both profiles before updating either balance.
            profiles = {
                profile.user_id: profile
                for profile in Profile.objects.select_for_update()
                .filter(user__in=users)
                .order_by("user_id")
            }

            sender_profile = profiles[request.user.pk]
            receiver_profile = profiles[receiver.pk]

            if sender_profile.balance < amount:
                raise ValueError("Insufficient balance.")

            sender_profile.balance -= amount
            receiver_profile.balance += amount

            sender_profile.save(update_fields=["balance"])
            receiver_profile.save(update_fields=["balance"])

        InternshipTransfer.objects.create(
            user=request.user,
            receiver=receiver,
            receiver_username=receiver.username,
            amount=amount,
            status="SUCCESS",
            seen_by_sender=False,
            seen_by_receiver=False
        )

        request.session.pop("pending_internal_transfer", None)

        messages.success(
            request,
            f"Successfully sent {amount:.2f} USDT to {receiver.username}."
        )

        return redirect("dashboard")

    except User.DoesNotExist:
        messages.error(request, "Recipient account no longer exists.")

    except (ValueError, KeyError, InvalidOperation):
        messages.error(request, "Transfer could not be completed. Please check your balance and try again.")

    return redirect("internal_transfer")
