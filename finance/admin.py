from django.contrib import admin

from .models import (
    Deposit,
    Withdrawal,
    ProfitClaim
)

from accounts.models import (
    Profile,
    ReferralBonus
)
from decimal import Decimal
from django.utils.html import format_html

@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "amount",
        "status",
        "proof",
        "created_at",
    )

    list_editable = (
        "status",
    )

    list_filter = (
        "status",
    )

    fields = (
        "user",
        "amount",
        "proof",
        "status",
    )

    readonly_fields = (
        "user",
        "amount",
        "proof",
    )

    def save_model(self, request, obj, form, change):

        try:
            super().save_model(
                request,
                obj,
                form,
                change
            )

            if obj.status == "Approved" and not obj.credited:

                profile = Profile.objects.get(
                    user=obj.user
                )

                profile.balance += obj.amount
                profile.total_deposit += obj.amount
                profile.save()

                if profile.referrer:

                    ReferralBonus.objects.create(
                        referrer=profile.referrer,
                        referred_user=obj.user,
                        rate=Decimal("0.01")
                    )

                obj.credited = True
                obj.save()

        except Exception as e:

            print("ERROR TYPE:", type(e))
            print("ERROR MESSAGE:", str(e))

            raise

@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "amount",
        "wallet_address",
        "status",
        "created_at"
    )

    search_fields = (
        "user__username",
        "wallet_address",
    )

    list_filter = (
        "status",
    )

    readonly_fields = (
        "wallet_address",
    )

    list_editable = (
        "status",
    )

    def save_model(
        self,
        request,
        obj,
        form,
        change
    ):

        super().save_model(
            request,
            obj,
            form,
            change
        )

        if (
            obj.status == "Approved"
            and not obj.processed
        ):

            profile = Profile.objects.get(
                user=obj.user
            )

            if profile.balance >= obj.amount:

                profile.balance -= obj.amount
                profile.save()

                obj.processed = True
                obj.save()