from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/list/(?P<list_id>\w+)/$', consumers.ShoppingListConsumer.as_asgi()),
]

