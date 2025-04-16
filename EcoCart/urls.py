from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),  # Django Admin 面板
    path("users/", include("users.urls")),  # 用户 API
    #path("accounts/", include("allauth.urls")),  # 🔥 社交登录 URL
    # project/urls.py
    path('shopping/', include('shopping.urls')),

]
