from celery import shared_task
from django.core.mail import send_mail
from datetime import datetime, timedelta
from .models import ShoppingItem
from django.contrib.auth.models import User

@shared_task
def check_expiring_products():
    today = datetime.today().date()
    soon_expiry_date = today + timedelta(days=3)

    # 查找即将过期的商品
    expiring_items = ShoppingItem.objects.filter(
        expiration_date__lte=soon_expiry_date,
        expiration_date__gte=today,
        reminder_sent=False
    )

    for item in expiring_items:
        user = item.list.owner
        # 发送提醒邮件（根据你的需求，可以改为推送通知等）
        send_mail(
            'Your product is about to expire!',
            f'The product "{item.product.name}" will expire on {item.expiration_date}.',
            None,  # 使用默认邮箱
            [user.email],
            fail_silently=False,
        )

        item.reminder_sent = True
        item.save()
