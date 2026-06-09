import random
import secrets

from django.core.mail import send_mail
from django.conf import settings


def generate_otp():
    return str(random.randint(100000, 999999))


def generate_token():
    return secrets.token_urlsafe(32)


def send_verification_email(user, token):

    verify_url = (
        f"http://127.0.0.1:8000/verify-email/{token}/"
    )

    subject = "Verify Your Email"

    message = f"""
Hello {user.username},

Thank you for registering.

Click the link below to verify your email:

{verify_url}

If you did not create this account, ignore this email.
"""

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False
    )


def send_login_otp(user, otp):

    subject = "Your Login Verification Code"

    message = f"""
Hello {user.username},

Your login code is:

{otp}

This code expires in 5 minutes.
"""

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False
    )

def send_password_reset_email(user, token):

    reset_url = (
        f"http://127.0.0.1:8000/reset-password/{token}/"
    )

    subject = "Reset Password"

    message = f"""
Hello {user.username},

Click the link below to reset your password:

{reset_url}

If you did not request this change, ignore this email.
"""

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False
    )

from django.core.mail import send_mail
from django.conf import settings


def send_otp_email(email, username, otp, amount, wallet_address):

    subject = "Withdrawal OTP Verification"

    message = f"""
Dear {username},

We received a request to withdraw {amount} USDT to the TRC20 wallet below:

Wallet Address:
{wallet_address}

To confirm this transaction, please enter the following One-Time Password (OTP):

{otp}

This OTP is valid for 10 minutes.

If you did not request this withdrawal, please ignore this email immediately and consider changing your password to protect your account.

Best regards,
Internship Saving Team
"""

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )

from django.core.mail import send_mail
from django.conf import settings


def send_transaction_notification(
    email,
    username,
    transaction_type,
    status,
    amount
):

    subject = f"{transaction_type} {status}"

    if status == "Approved":

        message = f"""
Dear {username},

Your {transaction_type.lower()} request of {amount} USDT has been approved successfully.

Thank you for using Internship Saving.

Best regards,
Internship Saving Team
"""

    else:

        message = f"""
Dear {username},

Your {transaction_type.lower()} request of {amount} USDT has been rejected.

If you believe this is a mistake, please contact support.

Best regards,
Internship Saving Team
"""

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )

def send_password_otp(email, otp):
    subject = "Password Change Verification"

    message = f"""
Hello,

Use this OTP to confirm your password change:

OTP: {otp}

If you did not request this, ignore this email.
"""

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False
    )