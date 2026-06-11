from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.db.models import Max
from .models import SupportMessage


@login_required
def support_chat(request):

    SupportMessage.objects.filter(
        receiver=request.user,
        seen=False
    ).update(
        seen=True
    )

    messages = (
        SupportMessage.objects.filter(sender=request.user)
        |
        SupportMessage.objects.filter(receiver=request.user)
    ).order_by("created_at")

    return render(
        request,
        "support/chat.html",
        {
            "messages": messages
        }
    )


@login_required
def send_message(request):

    if request.method == "POST":

        admin_user = User.objects.filter(
            is_superuser=True
        ).first()

        SupportMessage.objects.create(
            sender=request.user,
            receiver=admin_user,
            message=request.POST.get("message"),
            image=request.FILES.get("image"),
            voice=request.FILES.get("voice")
        )

        return JsonResponse({
            "success": True
        })

    return JsonResponse({
        "success": False
    })


@login_required
def get_messages(request):

    messages = (
        SupportMessage.objects.filter(sender=request.user)
        |
        SupportMessage.objects.filter(receiver=request.user)
    ).order_by("created_at")

    data = []

    for msg in messages:

        data.append({
            "id": msg.id,
            "sender": msg.sender.username,
            "message": msg.message or "",
            "image": msg.image.url if msg.image else "",
            "voice": msg.voice.url if msg.voice else "",
            "time": msg.created_at.strftime("%H:%M")
        })

    return JsonResponse(data, safe=False)


@staff_member_required
def admin_support(request):

    users = User.objects.filter(
        sent_support_messages__receiver=request.user
    ).distinct()

    user_data = []

    for user in users:

        unread = SupportMessage.objects.filter(
            sender=user,
            receiver=request.user,
            seen=False
        ).count()

        user_data.append({
            "user": user,
            "unread": unread
        })

    selected_user = None
    messages = []

    user_id = request.GET.get("user")

    if user_id:

        selected_user = User.objects.get(id=user_id)

        SupportMessage.objects.filter(
            sender=selected_user,
            receiver=request.user,
            seen=False
        ).update(seen=True)

        messages = (
            SupportMessage.objects.filter(
                sender=selected_user,
                receiver=request.user
            ) |
            SupportMessage.objects.filter(
                sender=request.user,
                receiver=selected_user
            )
        ).order_by("created_at")

    return render(
        request,
        "support/admin_chat.html",
        {
            "user_data": user_data,
            "selected_user": selected_user,
            "messages": messages
        }
    )
@staff_member_required
def admin_get_messages(request):

    user_id = request.GET.get("user")

    if not user_id:
        return JsonResponse([], safe=False)

    selected_user = User.objects.get(id=user_id)

    messages = (
        SupportMessage.objects.filter(sender=selected_user)
        |
        SupportMessage.objects.filter(receiver=selected_user)
    ).order_by("created_at")

    data = []

    for msg in messages:

        data.append({
            "sender": msg.sender.username,
            "is_admin": msg.sender.is_staff,
            "message": msg.message or "",
            "image": msg.image.url if msg.image else "",
            "voice": msg.voice.url if msg.voice else "",
            "time": msg.created_at.strftime("%H:%M")
        })

    return JsonResponse(data, safe=False)


@staff_member_required
def admin_send_message(request):

    if request.method == "POST":

        user_id = request.POST.get("user_id")

        selected_user = User.objects.get(
            id=user_id
        )

        SupportMessage.objects.create(
            sender=request.user,
            receiver=selected_user,
            message=request.POST.get("message"),
            image=request.FILES.get("image"),
            voice=request.FILES.get("voice")
        )

        return JsonResponse({
            "success": True
        })

    return JsonResponse({
        "success": False
    })

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User

from .models import SupportMessage


@staff_member_required
def admin_chat(request, user_id):

    user = get_object_or_404(
        User,
        id=user_id
    )

    messages = (
        SupportMessage.objects.filter(
            sender=user,
            receiver=request.user
        ) |
        SupportMessage.objects.filter(
            sender=request.user,
            receiver=user
        )
    ).order_by("created_at")

    SupportMessage.objects.filter(
        sender=user,
        receiver=request.user,
        seen=False
    ).update(seen=True)

    users = User.objects.filter(
        sent_support_messages__receiver=request.user
    ).distinct()

    return render(
        request,
        "support/admin_chat.html",
        {
            "users": users,
            "selected_user": user,   # ← ingenzi cyane
            "messages": messages
        }
    )

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.shortcuts import render
from .models import SupportMessage


@staff_member_required
def admin_chat_list(request):

    users = User.objects.filter(
        sent_support_messages__receiver=request.user
    ).distinct()

    user_data = []

    for user in users:

        unread = SupportMessage.objects.filter(
            sender=user,
            receiver=request.user,
            seen=False
        ).count()

        user_data.append({
            "user": user,
            "unread": unread
        })
    print("USERS:", users)
    print("USER DATA:", user_data)

    return render(
        request,
        "support/chat_list.html",
        {
            "user_data": user_data
        }
    )

Nta kibazo, reka tugende buhoro buhoro. Iki gice cyose kijya muri support app, si muri dashboard.

1. Shyira view muri support/views.py

Fungura:

support/views.py

Hasi cyane (cyangwa ahandi hose muri iyo file) wongereho:

from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def admin_unread_counts(request):

    data = []

    users = User.objects.filter(
        is_staff=False
    )

    for user in users:

        unread = SupportMessage.objects.filter(
            sender=user,
            receiver=request.user,
            seen=False
        ).count()

        data.append({
            "id": user.id,
            "unread": unread
        })

    return JsonResponse(
        data,
        safe=False
    )