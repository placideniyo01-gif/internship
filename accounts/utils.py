import random
import secrets


def generate_otp():
    return str(random.randint(100000, 999999))


def generate_token():
    return secrets.token_urlsafe(32)


def send_verification_email(user, token):
    return True


def send_login_otp(user, otp):
    return True


def send_password_reset_email(user, token):
    return True


def send_otp_email(email, username, otp, amount, wallet_address):
    return True


def send_transaction_notification(
    email,
    username,
    transaction_type,
    status,
    amount
):
    return True


def send_password_otp(email, otp):
    return True