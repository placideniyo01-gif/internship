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

import random

from accounts.models import EmailOTP

from accounts.utils import send_otp_email

from accounts.models import EmailOTP
from django.contrib import messages

