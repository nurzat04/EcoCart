from channels.generic.websocket import AsyncWebsocketConsumer

class ShoppingListConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.list_id = self.scope['url_route']['kwargs']['list_id']
        self.group_name = f'shopping_list_{self.list_id}'

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        # 广播给所有连接这个购物清单的用户
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'shopping_list_update',
                'message': text_data,
            }
        )

    async def shopping_list_update(self, event):
        await self.send(text_data=event['message'])

