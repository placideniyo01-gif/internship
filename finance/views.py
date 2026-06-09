from django.shortcuts import render
from django.shortcuts import redirect

from django.contrib.auth.decorators import login_required

from .models import Deposit

from django.contrib import messages

import random
from accounts.models import EmailOTP
from accounts.utils import send_otp_email

@login_required
def deposit(request):

    if request.method == "POST":

        amount = float(
            request.POST.get("amount")
        )

        if amount < 10:

            messages.error(
                request,
                "Minimum deposit is 10 USDT."
            )

            return redirect(
                "deposit"
            )

        proof = request.FILES.get(
            "proof"
        )

        Deposit.objects.create(
            user=request.user,
            amount=amount,
            proof=proof
        )

        messages.success(
            request,
            "Deposit submitted successfully."
        )

        return redirect(
            "deposit_history"
        )

    return render(
        request,
        "finance/deposit.html"
    )

from .models import Deposit, Withdrawal

@login_required
def deposit_history(request):

    deposits = Deposit.objects.filter(
        user=request.user
    ).order_by("-created_at")

    withdrawals = Withdrawal.objects.filter(
        user=request.user
    ).order_by("-created_at")

    return render(
        request,
        "finance/deposit_history.html",
        {
            "deposits": deposits,
            "withdrawals": withdrawals,
        }
    )

from decimal import Decimal

from accounts.models import (
    Profile,
    Referral
)

from .forms import WithdrawalForm
from django.utils import timezone
from datetime import timedelta
from .models import Withdrawal

@login_required
def withdraw(request):

    profile = Profile.objects.get(
        user=request.user
    )

    if request.method == "POST":

        form = WithdrawalForm(
            request.POST
        )

        if form.is_valid():

            amount = form.cleaned_data[
                "amount"
            ]

            active_referrals = Referral.objects.filter(
                referrer=request.user,
                referred_user__profile__total_deposit__gt=0
            ).count()

            last_withdrawal = Withdrawal.objects.filter(
                user=request.user
            ).order_by("-created_at").first()

            if last_withdrawal:

                next_date = (
                    last_withdrawal.created_at +
                    timedelta(days=7)
                )

                if timezone.now() < next_date:

                    form.add_error(
                        None,
                        f"You can only withdraw once every 7 days. Next withdrawal: {next_date.strftime('%d %b %Y')}"
                    )

                    return render(
                        request,
                        "finance/withdraw.html",
                        {
                            "form": form,
                            "balance": profile.balance,
                        }
                    )

            if active_referrals < 2:

                if amount < Decimal("100"):

                    form.add_error(
                        "amount",
                        "Minimum withdrawal is 100 USDT."
                    )

                    return render(
                        request,
                        "finance/withdraw.html",
                        {
                            "form": form,
                            "balance": profile.balance,
                        }
                    )

            if amount > profile.balance:

                form.add_error(
                    "amount",
                    "Insufficient balance."
                )

                return render(
                    request,
                    "finance/withdraw.html",
                    {
                        "form": form,
                        "balance": profile.balance,
                    }
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

            request.session["withdraw_amount"] = str(amount)
            request.session["wallet_address"] = form.cleaned_data["wallet_address"]

            wallet_address = form.cleaned_data["wallet_address"]

            send_otp_email(
                email=request.user.email,
                username=request.user.username,
                otp=otp,
                amount=amount,
                wallet_address=wallet_address
            )

            messages.success(
                request,
                "OTP has been sent to your email."
            )

            return redirect(
                "verify_withdraw_otp"
            )
    else:

        form = WithdrawalForm()

    print("Profile:", profile)
    print("Balance:", profile.balance)

    return render(
        request,
        "finance/withdraw.html",
        {
            "form": form,
            "balance": profile.balance
        }
    )

from accounts.models import EmailOTP
from django.contrib import messages

@login_required
def verify_withdraw_otp(request):

    if request.method == "POST":

        otp = request.POST.get("otp")

        otp_obj = EmailOTP.objects.filter(
            user=request.user,
            otp=otp,
            verified=False
        ).last()

        if not otp_obj:

            messages.error(
                request,
                "Invalid OTP."
            )

            return redirect(
                "verify_withdraw_otp"
            )

        if otp_obj.is_expired():

            messages.error(
                request,
                "OTP expired."
            )

            return redirect(
                "withdraw"
            )

        amount = request.session.get(
            "withdraw_amount"
        )

        wallet_address = request.session.get(
            "wallet_address"
        )

        Withdrawal.objects.create(
            user=request.user,
            amount=amount,
            wallet_address=wallet_address
        )

        otp_obj.verified = True
        otp_obj.save()

        del request.session[
            "withdraw_amount"
        ]

        del request.session[
            "wallet_address"
        ]

        messages.success(
            request,
            "Withdrawal request submitted successfully."
        )

        return redirect(
            "dashboard"
        )

    return render(
        request,
        "finance/verify_withdraw_otp.html"
    )
