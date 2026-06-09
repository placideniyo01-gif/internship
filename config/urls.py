from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from support import views as support_views

urlpatterns = [

    path(
        'admin/',
        admin.site.urls
    ),

    path(
        '',
        include('accounts.urls')
    ),

    path(
        'dashboard/',
        include('dashboard.urls')
    ),

    path(
        '',
        include('finance.urls')
    ),

    path(
        'support/',
        include('support.urls')
    ),

]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )