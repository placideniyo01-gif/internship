from django.urls import path
from . import views

urlpatterns = [

    path(
        "",
        views.support_chat,
        name="support_chat"
    ),

    path(
        "messages/",
        views.get_messages,
        name="get_messages"
    ),

    path(
        "send/",
        views.send_message,
        name="send_message"
    ),

    path(
        "admin-support/",
        views.admin_support,
        name="admin_support"
    ),

    path(
        "admin-messages/",
        views.admin_get_messages,
        name="admin_get_messages"
    ),

    path(
        "admin-send/",
        views.admin_send_message,
        name="admin_send_message"
    ),

    path(
        "admin-chat/",
        views.admin_chat_list,
        name="admin_chat_list"
    ),

    path(
        "admin-chat/<int:user_id>/",
        views.admin_chat,
        name="admin_chat"
    ),

]