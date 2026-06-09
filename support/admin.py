from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.contrib.admin.sites import NotRegistered
from django.urls import reverse
from django.utils.html import format_html

from .models import SupportMessage


# Banza uyikure muri admin niba yaranditswe
try:
    admin.site.unregister(User)
except NotRegistered:
    pass


class SupportUserAdmin(UserAdmin):

    list_display = (
        "username",
        "email",
        "unread_messages",
        "open_chat",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        return qs.filter(
            sent_support_messages__receiver__is_superuser=True
        ).distinct()

    def unread_messages(self, obj):
        count = SupportMessage.objects.filter(
            sender=obj,
            receiver__is_superuser=True,
            seen=False
        ).count()

        if count > 0:
            return format_html(
                '<span style="background:#22c55e;color:white;padding:4px 10px;border-radius:20px;">{} New</span>',
                count
            )

        return "-"

    unread_messages.short_description = "Unread"

    def open_chat(self, obj):
        url = reverse(
            "admin_chat",
            args=[obj.id]
        )

        return format_html(
            '<a class="button" href="{}">Open Chat</a>',
            url
        )

    open_chat.short_description = "Chat"


admin.site.register(User, SupportUserAdmin)