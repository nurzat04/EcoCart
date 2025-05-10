# consumers.py

from channels.generic.websocket import AsyncWebsocketConsumer
import json
from datetime import date, datetime, timedelta

class ShoppingListConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.list_id = self.scope['url_route']['kwargs']['list_id']
        self.group_name = f'shopping_list_{self.list_id}'

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            # 可加白名单校验，比如 data['action'] in ['add', 'remove', 'check']
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'shopping_list_update',
                    'message': json.dumps(data),  # 重新序列化，确保结构一致
                }
            )
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({'error': 'Invalid JSON'}))

    async def shopping_list_update(self, event):
        await self.send(text_data=event['message'])


class NotificationConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope['user']
        await self.accept()
        
        # Start checking for expiring items after the connection is established
        await self.check_expiring_items()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        # Here you can handle incoming messages
        await self.send(text_data=json.dumps({
            "message": f"You said: {text_data}"
        }))

    async def check_expiring_items(self):
        """ Check for expiring items in the user's shopping list and send reminders. """
        
        # Import models here after the connection is established
        from shopping.models import ShoppingItem

        today = date.today()

        # 查询即将过期且尚未勾选的商品
        expiring_items = ShoppingItem.objects.filter(
            list__owner=self.user,  # 通过 ShoppingList 的 owner 字段来获取与当前用户关联的购物清单
            expiration_date__lte=today + timedelta(days=7),  # 商品将在7天内过期
            is_checked=False,  # 忽略已勾选的商品
        )

        for item in expiring_items:
            # 发送 WebSocket 消息给用户
            await self.send(text_data=json.dumps({
                "message": f"Reminder: Your product '{item.product.name}' is expiring soon on {item.expiration_date}. Please check!"
            }))