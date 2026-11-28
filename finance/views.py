
import json
import logging
from decimal import Decimal, InvalidOperation
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST

from accounts.interest import settle_interest
from accounts.models import Profile, Referral

from .models import Deposit, Withdrawal, InternshipTransfer
from .forms import WithdrawalForm


logger = logging.getLogger(__name__)

PENDING_WITHDRAWAL_SESSION_KEY = "pending_withdrawal"
WITHDRAWAL_CONFIRMATION_TIMEOUT = 600


# =====================================================
# DEPOSIT
# Minimum deposit: 25 USDT
# =====================================================

@login_required
def deposit(request):

    if request.method == "POST":

        try:
            amount = Decimal(
                request.POST.get("amount", "").strip()
            )
        except (InvalidOperation, TypeError, ValueError):
            messages.error(
                request,
                "Please enter a valid deposit amount."
            )
            return redirect("deposit")

        if not amount.is_finite() or amount < Decimal("25"):
            messages.error(
                request,
                "Minimum deposit is 25 USDT."
            )
            return redirect("deposit")

        if amount != amount.quantize(Decimal("0.01")):
            messages.error(
                request,
                "Deposit amount cannot have more than 2 decimal places."
            )
            return redirect("deposit")

        proof = request.FILES.get("proof")

        if not proof:
            messages.error(
                request,
                "Please upload your deposit proof."
            )
            return redirect("deposit")

        Deposit.objects.create(
            user=request.user,
            amount=amount,
            proof=proof,
            status="Pending"
        )

        messages.success(
            request,
            "Deposit submitted successfully. Please wait for approval."
        )

        return redirect("deposit_history")

    return render(request, "finance/deposit.html")


# =====================================================
# DEPOSIT AND TRANSACTION HISTORY
# =====================================================

@login_required
def deposit_history(request):

    deposits = Deposit.objects.filter(
        user=request.user
    ).order_by("-created_at")

    withdrawals = Withdrawal.objects.filter(
        user=request.user
    ).order_by("-created_at")

    sent_internal_transfers = InternshipTransfer.objects.filter(
        user=request.user,
        receiver__isnull=False
    ).select_related(
        "receiver"
    ).order_by("-created_at")

    received_internal_transfers = InternshipTransfer.objects.filter(
        receiver=request.user
    ).select_related(
        "user"
    ).order_by("-created_at")

    return render(
        request,
        "finance/deposit_history.html",
        {
            "deposits": deposits,
            "withdrawals": withdrawals,
            "sent_internal_transfers": sent_internal_transfers,
            "received_internal_transfers": received_internal_transfers,
        }
    )


# =====================================================
# WITHDRAWAL VALIDATION
# Available Balance ONLY
# =====================================================

def validate_withdrawal_request(user, amount, settle=True):

    if not amount.is_finite() or amount <= Decimal("0"):
        return "Please enter a valid withdrawal amount."

    if amount != amount.quantize(Decimal("0.01")):
        return "Amount cannot have more than 2 decimal places."

    # Unlock expired blocked funds before checking balance.
    if settle:
        settle_interest(user, timezone.now())

    active_referrals = Referral.objects.filter(
        referrer=user,
        referred_user__profile__total_deposit__gt=0
    ).count()

    if active_referrals < 2 and amount < Decimal("50"):
        return "Minimum withdrawal is 50 USDT."

    last_withdrawal = Withdrawal.objects.filter(
        user=user
    ).order_by("-created_at").first()

    if last_withdrawal:

        next_date = last_withdrawal.created_at + timedelta(days=7)

        if timezone.now() < next_date:
            return (
                "You can only withdraw once every 7 days. "
                f"Next withdrawal: {next_date.strftime('%d %b %Y')}."
            )

    profile = Profile.objects.get(user=user)

    # IMPORTANT:
    # Only available balance can be withdrawn.
    # blocked_amount is never included here.
    if amount > profile.balance:
        return "Insufficient available balance."

    return None


# =====================================================
# WITHDRAWAL FORM
# Prepares confirmation only.
# Does NOT create a Withdrawal record.
# =====================================================

@login_required
def withdraw(request):

    # Settle interest and unlock expired blocked funds first.
    settle_interest(request.user, timezone.now())

    profile, created = Profile.objects.get_or_create(
        user=request.user
    )

    if request.method == "POST":

        form = WithdrawalForm(request.POST)

        if form.is_valid():

            amount = form.cleaned_data["amount"]
            wallet_address = form.cleaned_data["wallet_address"].strip()

            error = validate_withdrawal_request(
                request.user,
                amount,
                settle=False
            )

            if error:
                form.add_error(None, error)

            else:

                request.session[PENDING_WITHDRAWAL_SESSION_KEY] = {
                    "amount": str(amount),
                    "wallet_address": wallet_address,
                    "created_at": timezone.now().timestamp(),
                }

                request.session.modified = True

                return redirect("withdraw_confirm")

    else:
        form = WithdrawalForm()

    # Refresh profile after settlement.
    profile.refresh_from_db()

    return render(
        request,
        "finance/withdraw.html",
        {
            "form": form,
            "balance": profile.balance,
        }
    )


# =====================================================
# WITHDRAWAL CONFIRMATION
# Creates request ONLY after Confirm is clicked.
# =====================================================

@login_required
@require_http_methods(["GET", "POST"])
def withdraw_confirm(request):

    pending = request.session.get(
        PENDING_WITHDRAWAL_SESSION_KEY
    )

    if not pending:
        messages.error(
            request,
            "No pending withdrawal confirmation was found."
        )
        return redirect("withdraw")

    try:
        amount = Decimal(pending["amount"])
        wallet_address = pending["wallet_address"]
        created_at = float(pending["created_at"])

    except (KeyError, InvalidOperation, TypeError, ValueError):
        request.session.pop(
            PENDING_WITHDRAWAL_SESSION_KEY,
            None
        )

        messages.error(
            request,
            "Invalid withdrawal confirmation. Please try again."
        )

        return redirect("withdraw")

    if not amount.is_finite() or amount <= Decimal("0"):
        request.session.pop(
            PENDING_WITHDRAWAL_SESSION_KEY,
            None
        )

        messages.error(
            request,
            "Invalid withdrawal amount."
        )

        return redirect("withdraw")

    if timezone.now().timestamp() - created_at > WITHDRAWAL_CONFIRMATION_TIMEOUT:

        request.session.pop(
            PENDING_WITHDRAWAL_SESSION_KEY,
            None
        )

        messages.error(
            request,
            "Withdrawal confirmation expired. Please submit again."
        )

        return redirect("withdraw")

    # Settle before displaying confirmation.
    settle_interest(request.user, timezone.now())

    profile = Profile.objects.get(
        user=request.user
    )

    error = validate_withdrawal_request(
        request.user,
        amount,
        settle=False
    )

    if error:

        request.session.pop(
            PENDING_WITHDRAWAL_SESSION_KEY,
            None
        )

        messages.error(request, error)

        return redirect("withdraw")

    remaining_balance = profile.balance - amount

    if request.method == "POST":

        with transaction.atomic():

            # Settle any expired block before checking the balance.
            settle_interest(
                request.user,
                timezone.now()
            )

            locked_profile = Profile.objects.select_for_update().get(
                user=request.user
            )

            # Recheck withdrawal rules at confirmation time.
            error = validate_withdrawal_request(
                request.user,
                amount,
                settle=False
            )

            if error:

                request.session.pop(
                    PENDING_WITHDRAWAL_SESSION_KEY,
                    None
                )

                messages.error(request, error)

                return redirect("withdraw")

            # Final balance check using Available Balance only.
            if amount > locked_profile.balance:

                request.session.pop(
                    PENDING_WITHDRAWAL_SESSION_KEY,
                    None
                )

                messages.error(
                    request,
                    "Insufficient available balance."
                )

                return redirect("withdraw")

            Withdrawal.objects.create(
                user=request.user,
                amount=amount,
                wallet_address=wallet_address,
                status="Pending"
            )

            request.session.pop(
                PENDING_WITHDRAWAL_SESSION_KEY,
                None
            )

        messages.success(
            request,
            "Withdrawal request submitted successfully. Please wait for admin approval."
        )

        return redirect("dashboard")

    # Refresh values for confirmation page.
    profile.refresh_from_db()

    remaining_balance = profile.balance - amount

    return render(
        request,
        "finance/withdraw_confirm.html",
        {
            "amount": amount,
            "wallet_address": wallet_address,
            "balance": profile.balance,
            "remaining_balance": remaining_balance,
        }
    )


# =====================================================
# CANCEL WITHDRAWAL CONFIRMATION
# =====================================================

@login_required
@require_POST
def cancel_withdraw(request):

    request.session.pop(
        PENDING_WITHDRAWAL_SESSION_KEY,
        None
    )

    messages.info(
        request,
        "Withdrawal cancelled. No request was submitted."
    )

    return redirect("withdraw")


# =====================================================
# EXTERNAL WALLET TRANSFER API
# Credits Available Balance only.
# =====================================================

@csrf_exempt
@require_POST
def receive_wallet_transfer(request):

    try:
        data = json.loads(request.body)

        if not isinstance(data, dict):
            return JsonResponse(
                {
                    "success": False,
                    "message": "Invalid request data."
                },
                status=400
            )

        api_secret = getattr(
            settings,
            "API_TRANSFER_SECRET",
            None
        )

        if not api_secret or data.get("secret_key") != api_secret:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Unauthorized."
                },
                status=401
            )

        username = data.get("username")

        if not username:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Username is required."
                },
                status=400
            )

        try:
            amount = Decimal(
                str(data.get("amount", ""))
            )

        except (InvalidOperation, TypeError, ValueError):
            return JsonResponse(
                {
                    "success": False,
                    "message": "Invalid transfer amount."
                },
                status=400
            )

        if not amount.is_finite() or amount <= Decimal("0"):
            return JsonResponse(
                {
                    "success": False,
                    "message": "Transfer amount must be greater than zero."
                },
                status=400
            )

        if amount != amount.quantize(Decimal("0.01")):
            return JsonResponse(
                {
                    "success": False,
                    "message": "Amount cannot have more than 2 decimal places."
                },
                status=400
            )

        user = User.objects.filter(
            username=username
        ).first()

        if not user:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Username not found."
                },
                status=404
            )

        with transaction.atomic():

            # Settle expired blocks first.
            settle_interest(
                user,
                timezone.now()
            )

            profile = Profile.objects.select_for_update().get(
                user=user
            )

            # External transfer increases available balance.
            # It does not increase blocked amount.
            profile.balance += amount

            profile.save(
                update_fields=["balance"]
            )

            InternshipTransfer.objects.create(
                user=user,
                receiver=None,
                receiver_username=user.username,
                amount=amount,
                status="SUCCESS"
            )

        return JsonResponse(
            {
                "success": True,
                "message": "Transfer completed successfully."
            }
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {
                "success": False,
                "message": "Invalid JSON data."
            },
            status=400
        )

    except Exception:
        logger.exception(
            "External wallet transfer failed."
        )

        return JsonResponse(
            {
                "success": False,
                "message": "Transfer could not be completed."
            },
            status=500
        )
