from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.utils import OperationalError
from rest_framework import generics, serializers, status
from django.contrib.auth.password_validation import validate_password
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from wallets.models import Account

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, style={"input_type": "password"})
    def validate_password(self, value):
        validate_password(value)
        return value
    class Meta:
        model = User
        fields = ("id", "username", "password", "email")
    def create(self, validated_data):
        with transaction.atomic():
            user = User.objects.create_user(**validated_data)
            Token.objects.create(user=user)
        return user

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({"user_id": user.pk, "username": user.username, "token": user.auth_token.key}, status=status.HTTP_201_CREATED)

@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    try:
        from django.db import connection
        connection.ensure_connection()
        return Response({"status": "ok", "database": "connected"})
    except OperationalError:
        return Response({"status": "degraded", "database": "unavailable"}, status=503)

@api_view(["GET"])
def current_user(request):
    return Response({"id": request.user.id, "username": request.user.username, "is_staff": request.user.is_staff})
