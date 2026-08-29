from django.contrib import admin
from django.urls import path, include



urlpatterns = [
    path('api/', include("books.urls", namespace="books")),
    path('admin/', admin.site.urls),
]
