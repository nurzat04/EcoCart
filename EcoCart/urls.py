from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),  # Django Admin 面板
    path("users/", include("users.urls")),  # 用户 API
    #path("accounts/", include("allauth.urls")),  # 🔥 社交登录 URL
    # project/urls.py
    path('shopping/', include('shopping.urls')),

]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
