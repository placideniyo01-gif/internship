
from django.urls import path
from . import views

urlpatterns = [

    path(
        "deposit/",
        views.deposit,
        name="deposit"
    ),

    path(
        "deposit-history/",
        views.deposit_history,
        name="deposit_history"
    ),

    path(
        "withdraw/",
        views.withdraw,
        name="withdraw"
    ),

    path(
        "withdraw/confirm/",
        views.withdraw_confirm,
        name="withdraw_confirm"
    ),

    path(
        "withdraw/cancel/",
        views.cancel_withdraw,
        name="cancel_withdraw"
    ),

    path(
        "api/receive-wallet-transfer/",
        views.receive_wallet_transfer,
        name="receive_wallet_transfer"
    ),

]
