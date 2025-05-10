from channels.layers import get_channel_layer
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import ShoppingItem

@shared_task
def check_expiring_products():
    today = timezone.now().date()
    soon_expiry_date = today + timedelta(days=3)

    # 查找即将过期的商品
    expiring_items = ShoppingItem.objects.filter(
        expiration_date__lte=soon_expiry_date,
        expiration_date__gte=today,
        reminder_sent=False
    )

    for item in expiring_items:
        # 获取用户的 WebSocket 群组名
        group_name = f"user_{item.list.owner.id}"

        # 推送通知到 WebSocket 客户端
        channel_layer = get_channel_layer()
        channel_layer.group_send(
            group_name,  # 群组名
            {
                'type': 'send_notification',
                'message': f'Your product "{item.product.name}" will expire on {item.expiration_date}.'
            }
        )

        item.reminder_sent = True
        item.save()
