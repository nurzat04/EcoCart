# shopping/views_admin.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from users.models import CustomUser
from shopping.models import Product, ShoppingItem
from django.db.models import Count

class AdminDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_admin:
            return Response({'detail': 'Permission denied'}, status=403)

        # 最受欢迎商品（购买次数最多）
        popular_products = (
            ShoppingItem.objects.values('product__name')
            .annotate(count=Count('product'))
            .order_by('-count')[:5]
        )

        # 用户数量
        user_count = CustomUser.objects.count()

        # 活跃用户（有购物清单的）
        active_users = CustomUser.objects.filter(owned_shopping_lists__isnull=False).distinct().count()

        return Response({
            "user_count": user_count,
            "active_users": active_users,
            "top_products": popular_products,
        })
