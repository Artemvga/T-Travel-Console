from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.routes.models import RouteFavorite, RouteSearchLog

from .serializers import LoginSerializer, RegisterSerializer


User = get_user_model()


def _serialize_user(user):
    recent_searches = (
        RouteSearchLog.objects.filter(user=user)
        .select_related("from_city", "via_city", "to_city")
        .order_by("-created_at")[:6]
    )
    return {
        "id": user.id,
        "username": user.username,
        "date_joined": timezone.localtime(user.date_joined).isoformat(),
        "favorites_count": RouteFavorite.objects.filter(user=user).count(),
        "recent_searches": [
            {
                "id": item.id,
                "from_city": item.from_city.name if item.from_city else None,
                "from_city_slug": item.from_city.slug if item.from_city else None,
                "via_city": item.via_city.name if item.via_city else None,
                "via_city_slug": item.via_city.slug if item.via_city else None,
                "to_city": item.to_city.name if item.to_city else None,
                "to_city_slug": item.to_city.slug if item.to_city else None,
                "priority_mode": item.priority_mode,
                "departure_at": timezone.localtime(item.departure_at).isoformat(),
                "created_at": timezone.localtime(item.created_at).isoformat(),
            }
            for item in recent_searches
        ],
    }


class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.create_user(
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        Token.objects.filter(user=user).delete()
        token = Token.objects.create(user=user)

        return Response(
            {
                "token": token.key,
                "user": _serialize_user(user),
            },
            status=status.HTTP_201_CREATED,
        )


class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request=request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            return Response(
                {"detail": "Неверный логин или пароль."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        Token.objects.filter(user=user).delete()
        token = Token.objects.create(user=user)
        return Response(
            {
                "token": token.key,
                "user": _serialize_user(user),
            }
        )


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.auth:
            request.auth.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_serialize_user(request.user))
