from django.urls import path
from . import views

urlpatterns = [

    path("", views.dashboard, name="dashboard"),

    path("claim-interest/", views.claim_interest, name="claim_interest"),

    path("welcome/", views.welcome, name="welcome"),

    path("live-balance/", views.live_balance, name="live_balance"),

    path("claim-referral-bonus/", views.claim_bonus, name="claim_referral_bonus"),

    path(
        "settings/",
        views.settings_view,
        name="settings"
    ),

    path(
        "change-password/",
        views.change_password,
        name="change_password"
    ),

    path(
        "verify-password-otp/",
        views.verify_password_otp,
        name="verify_password_otp"
    ),

    path(
        "delete-account/",
        views.delete_account,
        name="delete_account"
    ),

    path(
        "dashboard/unread-support/",
        views.unread_support_count,
        name="unread_support_count"
    ),

]