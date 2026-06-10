from django.shortcuts import render
from django.shortcuts import redirect

from django.contrib.auth.decorators import login_required

from .models import Deposit

from django.contrib import messages


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
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils import timezone

from accounts.models import Profile, Referral
from .forms import WithdrawalForm
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

            # Create withdrawal directly
            Withdrawal.objects.create(
                user=request.user,
                amount=amount,
                wallet_address=form.cleaned_data[
                    "wallet_address"
                ]
            )

            messages.success(
                request,
                "Withdrawal request submitted successfully."
            )

            return redirect(
                "dashboard"
            )

    else:

        form = WithdrawalForm()

    return render(
        request,
        "finance/withdraw.html",
        {
            "form": form,
            "balance": profile.balance
        }
    )
