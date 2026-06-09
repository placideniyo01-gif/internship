from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Withdrawal
from .models import Deposit
from django.core.mail import send_mail
from django.conf import settings
from accounts.utils import send_transaction_notification
from accounts.models import (
    Profile,
    Referral,
    ReferralDeposit
)


@receiver(post_save, sender=Deposit)
def credit_balance(sender, instance, **kwargs):

    if (
        instance.status == "Approved"
        and not instance.credited
    ):

        profile = Profile.objects.get(
            user=instance.user
        )

        profile.balance += instance.amount
        profile.total_deposit += instance.amount
        profile.save()

        try:

            referral = Referral.objects.get(
                referred_user=instance.user
            )

            first_deposit = Deposit.objects.filter(
                user=instance.user,
                status="Approved"
            ).count()

            if first_deposit == 1:

                if instance.amount < 100:
                    rate = 0.001

                elif instance.amount < 500:
                    rate = 0.002

                else:
                    rate = 0.003

                ReferralDeposit.objects.create(
                    referral=referral,
                    deposit_amount=instance.amount,
                    bonus_rate=rate
                )

        except Referral.DoesNotExist:
            pass

        instance.credited = True
        instance.save()

@receiver(post_save, sender=Deposit)
def deposit_notification(sender, instance, created, **kwargs):

    if (
        instance.status == "Approved"
        and not instance.notification_sent
    ):

        send_mail(
            "Deposit Approved",
            f"Dear {instance.user.username},\n\n"
            f"Your deposit of {instance.amount} USDT has been approved successfully.",
            settings.DEFAULT_FROM_EMAIL,
            [instance.user.email],
            fail_silently=False,
        )

        instance.notification_sent = True
        instance.save(update_fields=["notification_sent"])
        
@receiver(post_save, sender=Withdrawal)
def withdrawal_notification(sender, instance, created, **kwargs):

    if (
        instance.status in ["Approved", "Rejected"]
        and not instance.notification_sent
    ):

        send_mail(
            f"Withdrawal {instance.status}",
            f"Dear {instance.user.username},\n\n"
            f"Your withdrawal request of {instance.amount} USDT "
            f"has been {instance.status.lower()}.",
            settings.DEFAULT_FROM_EMAIL,
            [instance.user.email],
            fail_silently=False,
        )

        instance.notification_sent = True
        instance.save(update_fields=["notification_sent"])