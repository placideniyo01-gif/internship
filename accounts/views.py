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
    EmailVerification
)

from .utils import (
    generate_token,
    send_verification_email
)
from .models import (
    Profile,
    EmailVerification,
    EmailOTP,
    PasswordReset,
    Referral
)

from .utils import (
    generate_otp,
    send_login_otp
)


from .models import PasswordReset
from .utils import (
    generate_token,
    send_password_reset_email
)

def login_view(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        print("LOGIN ATTEMPT")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user:
            profile = Profile.objects.get(user=user)

            print("USER =", user.username)
            print("ACTIVE =", user.is_active)
            print("VERIFIED =", profile.email_verified)

            if not profile.email_verified:

                messages.error(
                    request,
                    "Please verify your email first."
                )

                return redirect("login")

                print("BEFORE LOGIN")

                login(
                    request,
                    user
                )

                print("AFTER LOGIN")

                return redirect("welcome")

        messages.error(
            request,
            "Invalid username or password"
        )

    return render(
        request,
        "accounts/login.html"
    )

def verify_otp(request):

    user_id = request.session.get(
        "otp_user"
    )

    if not user_id:
        return redirect("login")

    user = User.objects.get(
        id=user_id
    )

    if request.method == "POST":

        entered_otp = request.POST.get(
            "otp"
        )

        otp_obj = EmailOTP.objects.filter(
            user=user,
            verified=False
        ).order_by("-created_at").first()

        if not otp_obj:

            messages.error(
                request,
                "OTP not found."
            )

            return redirect("login")

        if otp_obj.is_expired():

            messages.error(
                request,
                "OTP expired."
            )

            return redirect("login")

        if otp_obj.otp != entered_otp:

            messages.error(
                request,
                "Invalid OTP."
            )

            return redirect("verify_otp")

        otp_obj.verified = True
        otp_obj.save()

        login(
            request,
            user
        )

        request.session.pop(
            "otp_user",
            None
        )

        return redirect(
            "welcome"
        )

    return render(
        request,
        "accounts/verify_otp.html"
    )
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User

from .models import Profile, EmailVerification
from .utils import generate_token, send_verification_email


def signup_view(request):

    # Fata referral code muri URL
    ref_code = request.GET.get("ref")

    # Bika referral code muri session
    if ref_code:
        request.session["ref_code"] = ref_code

    if request.method == "POST":

        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")

        # Validation
        if User.objects.filter(
            username=username
        ).exists():

            messages.error(
                request,
                "Username already exists"
            )

            return redirect("signup")

        if User.objects.filter(
            email=email
        ).exists():

            messages.error(
                request,
                "Email already exists"
            )

            return redirect("signup")

        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_active=False
        )

        # Profile yakozwe na signal
        profile = Profile.objects.get(
            user=user
        )

        saved_ref_code = request.session.get(
            "ref_code"
        )

        print("REF CODE =", saved_ref_code)

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

        # Email verification
        token = generate_token()

        EmailVerification.objects.create(
            user=user,
            token=token
        )

        try:
            send_verification_email(
                user,
                token
            )
            print("EMAIL SENT SUCCESSFULLY")

        except Exception as e:
            print("EMAIL ERROR:", str(e))
            messages.error(
                request,
                f"Email Error: {e}"
            )
            return redirect("signup")

    return render(
        request,
        "accounts/signup.html"
    )
    
def verify_email(request, token):

    try:

        verification = EmailVerification.objects.get(
            token=token
        )

        user = verification.user

        user.is_active = True
        user.save()

        profile = Profile.objects.get(
            user=user
        )

        profile.email_verified = True
        profile.save()

        verification.delete()

        messages.success(
            request,
            "Email verified successfully."
        )

        return redirect("login")

    except EmailVerification.DoesNotExist:

        messages.error(
            request,
            "Invalid verification link."
        )

        return redirect("login")

def logout_view(request):
    logout(request)
    return redirect("login")


def forgot_password(request):

    if request.method == "POST":

        email = request.POST.get("email")

        try:

            user = User.objects.get(
                email=email
            )

            token = generate_token()

            PasswordReset.objects.create(
                user=user,
                token=token
            )

            send_password_reset_email(
                user,
                token
            )

            messages.success(
                request,
                "Password reset link sent."
            )

            return redirect("login")

        except User.DoesNotExist:

            messages.error(
                request,
                "Email not found."
            )

    return render(
        request,
        "accounts/forgot_password.html"
    )

def reset_password(request, token):

    try:

        reset_obj = PasswordReset.objects.get(
            token=token
        )

        if reset_obj.is_expired():

            messages.error(
                request,
                "Reset link expired."
            )

            return redirect(
                "forgot_password"
            )

    except PasswordReset.DoesNotExist:

        messages.error(
            request,
            "Invalid reset link."
        )

        return redirect(
            "forgot_password"
        )

    if request.method == "POST":

        password = request.POST.get(
            "password"
        )

        confirm_password = request.POST.get(
            "confirm_password"
        )

        if password != confirm_password:

            messages.error(
                request,
                "Passwords do not match."
            )

            return redirect(
                "reset_password",
                token=token
            )

        user = reset_obj.user

        user.set_password(
            password
        )

        user.save()

        reset_obj.delete()

        messages.success(
            request,
            "Password changed successfully."
        )

        return redirect(
            "login"
        )

    return render(
        request,
        "accounts/reset_password.html"
    )
