from django.db import models
from django.contrib.auth.models import User


class Deposit(models.Model):

    STATUS_CHOICES = (
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    proof = models.ImageField(
        upload_to="proofs/",
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Pending"
    )
    notification_sent = models.BooleanField(default=False)
    credited = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )



from django.utils import timezone

class ReferralBonus(models.Model):

    referrer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="earned_referrals"
    )

    referred_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="joined_by_referral"
    )

    rate = models.DecimalField(
        max_digits=5,
        decimal_places=3
    )

    started_at = models.DateTimeField(
        default=timezone.now
    )

    active = models.BooleanField(
        default=True
    )

    def __str__(self):
        return (
            f"{self.referrer.username}"
            f" -> "
            f"{self.referred_user.username}"
        )
        
class Withdrawal(models.Model):

    STATUS_CHOICES = (
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    wallet_address = models.CharField(
        max_length=255
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Pending"
    )

    processed = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    notification_sent = models.BooleanField(
        default=False
    )
    def __str__(self):
        return f"{self.user.username} - {self.amount}"

class ProfitClaim(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.user.username
