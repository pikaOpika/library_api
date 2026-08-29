from django.urls import path, include

from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from users.views import RegisterUser, ProfileUser


app_name = "users"


urlpatterns = [
    path("users/", RegisterUser.as_view(), name="register"),
    path("users/token/", TokenObtainPairView.as_view(), name="access-token"),
    path("users/token/refresh/", TokenRefreshView.as_view(), name="refresh-token"),
    path("users/me/", ProfileUser.as_view(), name="profile")
]
