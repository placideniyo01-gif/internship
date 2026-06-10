from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import (
    authenticate,
    login,
    logout
)
from django.contrib import messages

from .models import (
    Profile,
    Referral
)


def login_view(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user:

            login(
                request,
                user
            )

            return redirect(
                "welcome"
            )

        messages.error(
            request,
            "Invalid username or password"
        )

    return render(
        request,
        "accounts/login.html"
    )


def signup_view(request):

    ref_code = request.GET.get("ref")

    if ref_code:
        request.session["ref_code"] = ref_code

    if request.method == "POST":

        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")

        if User.objects.filter(
            username=username
        ).exists():

            messages.error(
                request,
                "Username already exists"
            )

            return redirect(
                "signup"
            )

        if User.objects.filter(
            email=email
        ).exists():

            messages.error(
                request,
                "Email already exists"
            )

            return redirect(
                "signup"
            )

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_active=True
        )

        profile = Profile.objects.get(
            user=user
        )

        saved_ref_code = request.session.get(
            "ref_code"
        )

        if saved_ref_code:

            try:

                ref_profile = Profile.objects.get(
                    referral_code=saved_ref_code
                )

                profile.referrer = ref_profile.user
                profile.save()

                Referral.objects.get_or_create(
                    referrer=ref_profile.user,
                    referred_user=user
                )

            except Profile.DoesNotExist:
                pass

        profile.email_verified = True
        profile.save()

        messages.success(
            request,
            "Account created successfully."
        )

        return redirect(
            "login"
        )

    return render(
        request,
        "accounts/signup.html"
    )


def logout_view(request):

    logout(request)

    return redirect(
        "login"
    )


def forgot_password(request):

    messages.error(
        request,
        "Password reset is currently unavailable."
    )

    return redirect(
        "login"
    )


def reset_password(request, token):

    messages.error(
        request,
        "Password reset is currently unavailable."
    )

    return redirect(
        "login"
    )


def verify_email(request, token):

    messages.error(
        request,
        "Email verification is disabled."
    )

    return redirect(
        "login"
    )


def verify_otp(request):

    messages.error(
        request,
        "OTP verification is disabled."
    )

    return redirect(
        "login"
    )