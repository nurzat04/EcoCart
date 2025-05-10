# routing.py

from django.urls import path, re_path
from .consumers import NotificationConsumer, ShoppingListConsumer

websocket_urlpatterns = [
    re_path(r'^ws/notifications/$', NotificationConsumer.as_asgi()),    
    path('ws/shopping-list/<str:list_id>/',ShoppingListConsumer.as_asgi()),  # 也顺便加上这个
]
