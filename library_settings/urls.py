from django.contrib import admin
from django.urls import path, include



urlpatterns = [
    path('api/', include("books.urls", namespace="books")),
    path('api/', include("users.urls", namespace="users")),
    path('api/', include("borrowings.urls", namespace="borrowings")),
    path('admin/', admin.site.urls),
]
