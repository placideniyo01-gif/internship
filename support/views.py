
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.views.decorators.http import require_GET, require_POST
from django.db.models import Q
from django.db import transaction

from .models import SupportMessage


def get_conversation(user1, user2):
    return SupportMessage.objects.filter(
        Q(sender=user1, receiver=user2) |
        Q(sender=user2, receiver=user1)
    ).select_related("sender", "receiver").order_by("created_at")


def get_admin_user():
    return User.objects.filter(is_superuser=True).first()


def get_admin_user_data(admin):
    users = User.objects.filter(
        sent_support_messages__receiver=admin
    ).distinct().order_by("username")

    user_data = []

    for user in users:
        unread = SupportMessage.objects.filter(
            sender=user,
            receiver=admin,
            seen=False
        ).count()

        user_data.append({
            "user": user,
            "unread": unread
        })

    return user_data


@login_required
def support_chat(request):
    SupportMessage.objects.filter(
        receiver=request.user,
        seen=False
    ).update(seen=True)

    messages = get_conversation(
        request.user,
        get_admin_user()
    ) if get_admin_user() else []

    return render(
        request,
        "support/chat.html",
        {"messages": messages}
    )


@login_required
@require_POST
def send_message(request):
    admin_user = get_admin_user()

    if not admin_user:
        return JsonResponse({
            "success": False,
            "error": "Support is currently unavailable."
        }, status=503)

    message = (request.POST.get("message") or "").strip()
    image = request.FILES.get("image")
    voice = request.FILES.get("voice")

    if not message and not image and not voice:
        return JsonResponse({
            "success": False,
            "error": "Write a message or attach a file."
        }, status=400)

    support_message = SupportMessage.objects.create(
        sender=request.user,
        receiver=admin_user,
        message=message,
        image=image,
        voice=voice
    )

    return JsonResponse({
        "success": True,
        "id": support_message.id
    })


@login_required
@require_GET
def get_messages(request):
    admin_user = get_admin_user()

    if not admin_user:
        return JsonResponse([], safe=False)

    messages = get_conversation(
        request.user,
        admin_user
    )

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
    user_data = get_admin_user_data(request.user)

    selected_user = None
    messages = []

    user_id = request.GET.get("user")

    if user_id:
        selected_user = get_object_or_404(
            User,
            id=user_id,
            is_staff=False
        )

        SupportMessage.objects.filter(
            sender=selected_user,
            receiver=request.user,
            seen=False
        ).update(seen=True)

        messages = get_conversation(
            selected_user,
            request.user
        )

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
@require_GET
def admin_get_messages(request):
    user_id = request.GET.get("user")

    if not user_id:
        return JsonResponse([], safe=False)

    selected_user = get_object_or_404(
        User,
        id=user_id,
        is_staff=False
    )

    messages = get_conversation(
        selected_user,
        request.user
    )

    data = []

    for msg in messages:
        data.append({
            "id": msg.id,
            "sender": msg.sender.username,
            "is_admin": msg.sender.is_staff,
            "message": msg.message or "",
            "image": msg.image.url if msg.image else "",
            "voice": msg.voice.url if msg.voice else "",
            "time": msg.created_at.strftime("%H:%M")
        })

    return JsonResponse(data, safe=False)


@staff_member_required
@require_POST
def admin_send_message(request):
    user_id = request.POST.get("user_id")

    selected_user = get_object_or_404(
        User,
        id=user_id,
        is_staff=False
    )

    message = (request.POST.get("message") or "").strip()
    image = request.FILES.get("image")
    voice = request.FILES.get("voice")

    if not message and not image and not voice:
        return JsonResponse({
            "success": False,
            "error": "Write a reply or attach a file."
        }, status=400)

    support_message = SupportMessage.objects.create(
        sender=request.user,
        receiver=selected_user,
        message=message,
        image=image,
        voice=voice
    )

    return JsonResponse({
        "success": True,
        "id": support_message.id
    })


@staff_member_required
def admin_chat(request, user_id):
    selected_user = get_object_or_404(
        User,
        id=user_id,
        is_staff=False
    )

    SupportMessage.objects.filter(
        sender=selected_user,
        receiver=request.user,
        seen=False
    ).update(seen=True)

    return render(
        request,
        "support/admin_chat.html",
        {
            "user_data": get_admin_user_data(request.user),
            "selected_user": selected_user,
            "messages": get_conversation(
                selected_user,
                request.user
            )
        }
    )


@staff_member_required
def admin_chat_list(request):
    return render(
        request,
        "support/chat_list.html",
        {
            "user_data": get_admin_user_data(request.user)
        }
    )


@staff_member_required
@require_GET
def admin_unread_counts(request):
    users = User.objects.filter(
        is_staff=False
    )

    data = []

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

    return JsonResponse(data, safe=False)
