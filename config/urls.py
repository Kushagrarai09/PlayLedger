from django.contrib import admin
from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token
from accounts.views import RegisterView, health_check, current_user
urlpatterns = [path("admin/", admin.site.urls), path("api/health/", health_check), path("api/auth/register/", RegisterView.as_view()), path("api/auth/login/", obtain_auth_token), path("api/auth/me/", current_user), path("api/", include("wallets.urls")), path("api/", include("ledger.urls"))]
