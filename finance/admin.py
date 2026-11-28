
from django.contrib import admin
from django.utils.html import format_html

from .models import Deposit, Withdrawal, ProfitClaim


# =====================================================
# DEPOSIT ADMIN
# Deposit processing is handled by finance/signals.py
# =====================================================

@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "amount",
        "status",
        "view_proof",
        "credited",
        "created_at",
    )

    list_filter = (
        "status",
        "credited",
        "created_at",
    )

    search_fields = (
        "user__username",
    )

    readonly_fields = (
        "user",
        "amount",
        "proof",
        "view_proof",
        "credited",
        "created_at",
    )

    fields = (
        "user",
        "amount",
        "proof",
        "view_proof",
        "status",
        "credited",
        "created_at",
    )

    def get_readonly_fields(self, request, obj=None):

        readonly = list(
            super().get_readonly_fields(request, obj)
        )

        # Once credited, deposit status cannot be changed.
        if obj and obj.credited:
            readonly.append("status")

        return readonly

    @admin.display(description="Proof")
    def view_proof(self, obj):

        if obj.proof:
            return format_html(
                '<a href="{}" target="_blank" rel="noopener">'
                'View Proof</a>',
                obj.proof.url
            )

        return "No Proof"


# =====================================================
# WITHDRAWAL ADMIN
# Withdrawal processing is handled by finance/signals.py
# =====================================================

@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "amount",
        "wallet_address",
        "status",
        "processed",
        "created_at",
    )

    search_fields = (
        "user__username",
        "wallet_address",
    )

    list_filter = (
        "status",
        "processed",
        "created_at",
    )

    readonly_fields = (
        "user",
        "amount",
        "wallet_address",
        "processed",
        "created_at",
    )

    fields = (
        "user",
        "amount",
        "wallet_address",
        "status",
        "processed",
        "created_at",
    )

    def get_readonly_fields(self, request, obj=None):

        readonly = list(
            super().get_readonly_fields(request, obj)
        )

        # Once processed, withdrawal status cannot be changed.
        if obj and obj.processed:
            readonly.append("status")

        return readonly


# =====================================================
# PROFIT CLAIM ADMIN
# =====================================================

@admin.register(ProfitClaim)
class ProfitClaimAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "amount",
        "created_at",
    )

    search_fields = (
        "user__username",
    )

    list_filter = (
        "created_at",
    )
