
from django.contrib import admin, messages
from django.db import transaction
from django.utils.html import format_html

from decimal import Decimal

from .models import Deposit, Withdrawal, ProfitClaim
from accounts.models import Profile, ReferralBonus
from accounts.interest import settle_interest


@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "amount",
        "status",
        "view_proof",
        "created_at",
    )

    list_editable = ("status",)
    list_filter = ("status",)

    readonly_fields = (
        "user",
        "amount",
        "proof",
        "view_proof",
    )

    fields = (
        "user",
        "amount",
        "proof",
        "view_proof",
        "status",
    )

    def view_proof(self, obj):
        if obj.proof:
            return format_html(
                '<a href="{}" target="_blank">View Proof</a>',
                obj.proof.url
            )
        return "No Proof"

    view_proof.short_description = "Proof"

    def save_model(self, request, obj, form, change):

        with transaction.atomic():

            # Save the admin changes first.
            super().save_model(request, obj, form, change)

            # Lock the deposit to prevent duplicate crediting.
            deposit = Deposit.objects.select_for_update().get(
                pk=obj.pk
            )

            if deposit.status == "Approved" and not deposit.credited:

                # Settle interest BEFORE increasing the balance.
                settle_interest(
                    deposit.user,
                )

                profile = Profile.objects.select_for_update().get(
                    user=deposit.user
                )

                profile.balance += deposit.amount
                profile.total_deposit += deposit.amount

                profile.save(update_fields=[
                    "balance",
                    "total_deposit",
                ])

                # Create referral bonus only once.
                if profile.referrer:
                    ReferralBonus.objects.create(
                        referrer=profile.referrer,
                        referred_user=deposit.user,
                        rate=Decimal("0.01")
                    )

                deposit.credited = True
                deposit.save(update_fields=["credited"])

                obj.credited = True


@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "amount",
        "wallet_address",
        "status",
        "created_at",
    )

    search_fields = (
        "user__username",
        "wallet_address",
    )

    list_filter = ("status",)
    list_editable = ("status",)

    readonly_fields = ("wallet_address",)

    def save_model(self, request, obj, form, change):

        with transaction.atomic():

            super().save_model(request, obj, form, change)

            # Lock withdrawal to prevent duplicate processing.
            withdrawal = Withdrawal.objects.select_for_update().get(
                pk=obj.pk
            )

            if withdrawal.status == "Approved" and not withdrawal.processed:

                # Settle interest BEFORE reducing the balance.
                settle_interest(
                    withdrawal.user,
                )

                profile = Profile.objects.select_for_update().get(
                    user=withdrawal.user
                )

                if profile.balance >= withdrawal.amount:

                    profile.balance -= withdrawal.amount

                    profile.save(update_fields=["balance"])

                    withdrawal.processed = True
                    withdrawal.save(update_fields=["processed"])

                    obj.processed = True

                else:

                    # Do not approve a withdrawal without sufficient funds.
                    withdrawal.status = "Pending"
                    withdrawal.save(update_fields=["status"])

                    obj.status = "Pending"

                    self.message_user(
                        request,
                        "Withdrawal was not approved: insufficient balance.",
                        level=messages.ERROR
                    )


@admin.register(ProfitClaim)
class ProfitClaimAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "amount",
        "created_at",
    )
