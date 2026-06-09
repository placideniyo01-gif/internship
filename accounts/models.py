from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import uuid


class Profile(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    total_deposit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    total_earned = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    referral_code = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True
    )

    referrer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referred_users"
    )

    email_verified = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = str(uuid.uuid4())[:8].upper()

        super().save(*args, **kwargs)

    def __str__(self):
        return self.user.username


class EmailOTP(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    otp = models.CharField(
        max_length=6
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    verified = models.BooleanField(
        default=False
    )

    def is_expired(self):
        return timezone.now() > (
            self.created_at + timedelta(minutes=5)
        )

    def __str__(self):
        return f"{self.user.username} - {self.otp}"


class Referral(models.Model):

    referrer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="my_referrals"
    )

    referred_user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="invited_by"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.referrer.username} -> {self.referred_user.username}"

class ReferralDeposit(models.Model):

    referral = models.ForeignKey(
        Referral,
        on_delete=models.CASCADE
    )

    deposit_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    bonus_rate = models.DecimalField(
        max_digits=5,
        decimal_places=3,
        default=0.01
    )

    started_at = models.DateTimeField(
        auto_now_add=True
    )

    active = models.BooleanField(
        default=True
    )

    claimed_bonus = models.DecimalField(
        max_digits=18,
        decimal_places=8,
        default=0
    )

    def __str__(self):
        return str(
            self.referral.referred_user.username
        )

class ReferralBonus(models.Model):

    referral = models.ForeignKey(
        Referral,
        on_delete=models.CASCADE
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    claimed = models.BooleanField(
        default=False
    )

    def __str__(self):
        return f"{self.referral.referrer.username} bonus"


class InterestWallet(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    amount = models.DecimalField(
        max_digits=15,
        decimal_places=8,
        default=0
    )

    last_update = models.DateTimeField(
        default=timezone.now
    )

    def __str__(self):
        return self.user.username

class EmailVerification(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    token = models.CharField(
        max_length=255
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.user.username

class PasswordReset(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    token = models.CharField(
        max_length=255
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def is_expired(self):
        return timezone.now() > (
            self.created_at + timedelta(hours=1)
        )

    def __str__(self):
        return self.user.username