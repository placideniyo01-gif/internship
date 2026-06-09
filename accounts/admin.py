from django.contrib import admin
from .models import (
    Profile,
    EmailOTP,
    EmailVerification
)

admin.site.register(Profile)
admin.site.register(EmailOTP)
admin.site.register(EmailVerification)