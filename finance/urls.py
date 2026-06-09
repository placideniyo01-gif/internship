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
        "verify-withdraw-otp/",
        views.verify_withdraw_otp,
        name="verify_withdraw_otp"
    ),

]