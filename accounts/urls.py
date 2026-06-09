from django.urls import path
from . import views

urlpatterns = [
    path("", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("logout/", views.logout_view, name="logout"),
    path("forgot-password/", views.forgot_password, name="forgot_password"),

    path(
        "verify-email/<str:token>/",
        views.verify_email,
        name="verify_email"
    ),
  
    path(
        "verify-otp/",
        views.verify_otp,
        name="verify_otp"
    ),

    path(
        "reset-password/<str:token>/",
        views.reset_password,
        name="reset_password"
    ),

]