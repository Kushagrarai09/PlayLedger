
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

User = get_user_model()

# Django may already have registered the default User model.
# Unregister it before applying the custom UserAdmin.
if admin.site.is_registered(User):
    admin.site.unregister(User)

admin.site.register(User, UserAdmin)
