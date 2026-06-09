from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
from decimal import Decimal
from accounts.models import EmailOTP
from accounts.utils import send_otp_email  # niba ihari
from accounts.utils import send_password_otp
from django.contrib import messages
from support.models import SupportMessage
from accounts.models import EmailOTP
from accounts.models import (
    Profile,
    InterestWallet,
    Referral,
    ReferralDeposit
)


@login_required
def dashboard(request):

    profile = Profile.objects.get(
        user=request.user
    )

    wallet, created = InterestWallet.objects.get_or_create(
        user=request.user
    )

    now = timezone.now()

    # ======================
    # NORMAL 4% INTEREST
    # ======================

    seconds = (
        now - wallet.last_update
    ).total_seconds()

    daily_rate = Decimal("0.04")

    interest_per_second = (
        profile.balance * daily_rate
    ) / Decimal("86400")

    earned_interest = (
        Decimal(str(seconds))
        * interest_per_second
    )

    current_interest = (
        wallet.amount +
        earned_interest
    )

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

        # TEST MODE
        # Locked -> Active after 1 hour

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

    context = {

        "username":
        request.user.username,

        "balance":
        round(profile.balance, 6),

        "interest":
        round(current_interest, 6),

        "interest_rate_per_second":
        float(interest_per_second),

        "referrals":
        referrals_count,

        "active_bonus":
        round(active_bonus, 6),

        "locked_bonus":
        round(locked_bonus, 6),

        "referral_profit":
        round(referral_profit, 6),

        "daily_ref_bonus_percent":
        round(total_bonus_rate, 2),

        "team":
        referrals_qs,

        "referral_code":
        profile.referral_code,

        "referral_link":
        referral_link,

        "unread_support":
        unread_support
    }

    return render(
        request,
        "dashboard/dashboard.html",
        context
    )


@login_required
def claim_bonus(request):

    profile = Profile.objects.get(
        user=request.user
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
def claim_interest(request):

    profile = Profile.objects.get(
        user=request.user
    )

    wallet, created = InterestWallet.objects.get_or_create(
        user=request.user
    )

    now = timezone.now()

    seconds = (
        now - wallet.last_update
    ).total_seconds()

    daily_rate = Decimal("0.04")

    interest_per_second = (
        profile.balance * daily_rate
    ) / Decimal("86400")

    earned_interest = (
        Decimal(str(seconds))
        * interest_per_second
    )

    total_interest = (
        wallet.amount +
        earned_interest
    )

    profile.balance += total_interest

    profile.total_earned += total_interest

    profile.save()

    wallet.amount = Decimal("0")
    wallet.last_update = now
    wallet.save()

    return redirect(
        "dashboard"
    )


@login_required
def live_balance(request):

    profile = Profile.objects.get(
        user=request.user
    )

    wallet, created = InterestWallet.objects.get_or_create(
        user=request.user
    )

    now = timezone.now()

    seconds = (
        now - wallet.last_update
    ).total_seconds()

    daily_rate = Decimal("0.04")

    interest_per_second = (
        profile.balance * daily_rate
    ) / Decimal("86400")

    earned_interest = (
        Decimal(str(seconds))
        * interest_per_second
    )

    current_interest = (
        wallet.amount +
        earned_interest
    )

    active_bonus = Decimal("0")
    locked_bonus = Decimal("0")
    referral_profit = Decimal("0")

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

        if days >= 30:
            active_bonus += available_bonus
        else:
            locked_bonus += available_bonus

    return JsonResponse({

        "balance":
        float(profile.balance),

        "interest":
        float(current_interest),

        "active_bonus":
        float(active_bonus),

        "locked_bonus":
        float(locked_bonus),

        "referral_profit":
        float(referral_profit)

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
        amount = request.POST.get('amount', 0)
        wallet_address = request.POST.get('wallet_address')
        current = request.POST.get(
            "current_password"
        )

        new = request.POST.get(
            "new_password"
        )

        if not request.user.check_password(current):

            messages.error(
                request,
                "Current password incorrect"
            )

            return redirect(
                "change_password"
            )

        otp = str(
            random.randint(
                100000,
                999999
            )
        )

        EmailOTP.objects.create(
            user=request.user,
            otp=otp
        )

        request.session[
            "new_password"
        ] = new

        send_password_otp(
            request.user.email,
            otp
        )

        return redirect(
            "verify_password_otp"
        )

    return render(
        request,
        "dashboard/change_password.html"
    )

@login_required
def verify_password_otp(request):

    if request.method == "POST":

        otp = request.POST.get(
            "otp"
        )

        obj = EmailOTP.objects.filter(
            user=request.user,
            otp=otp,
            verified=False
        ).last()

        if not obj:

            messages.error(
                request,
                "Invalid OTP"
            )

            return redirect(
                "verify_password_otp"
            )

        if obj.is_expired():

            messages.error(
                request,
                "OTP expired"
            )

            return redirect(
                "change_password"
            )

        request.user.set_password(
            request.session[
                "new_password"
            ]
        )

        request.user.save()

        obj.verified = True
        obj.save()

        messages.success(
            request,
            "Password changed successfully"
        )

        return redirect(
            "login"
        )

    return render(
        request,
        "dashboard/verify_password.html"
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