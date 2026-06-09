from django.db import models
from django.contrib.auth.models import User


class SupportMessage(models.Model):

    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_support_messages"
    )

    receiver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="received_support_messages"
    )

    message = models.TextField(
        blank=True,
        null=True
    )

    image = models.ImageField(
        upload_to="support/images/",
        blank=True,
        null=True
    )

    voice = models.FileField(
        upload_to="support/voices/",
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    seen = models.BooleanField(
        default=False
    )

    def __str__(self):
        return self.sender.username