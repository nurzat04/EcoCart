from django.http import JsonResponse
from rest_framework import viewsets, permissions, status, filters
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response

from shopping.tasks import check_expiring_products
from .models import ShoppingList, ShoppingItem, Product, ProductSupplier, Supplier, Category, Discount
from .serializers import ShoppingListSerializer, ShoppingItemSerializer, ProductSerializer, ProductSupplierSerializer, SupplierSerializer, CategorySerializer, DiscountSerializer
from users.permissions import IsVendorOrAdmin, IsVendor
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone
from datetime import datetime, timedelta
from django.db import models
from django.db.models import Count, Q, F, Min
from users.models import Contact, CustomUser

class SupplierListView(viewsets.ModelViewSet):
    queryset = Supplier.objects.select_related('user').filter(user__is_vendor=True)
    serializer_class = SupplierSerializer

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class ProductListView(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']

    def get_queryset(self):
        queryset = Product.objects.all()

        # 获取查询参数 category 并过滤
        category_name = self.request.GET.get('category')
        if category_name:
            try:
                category = Category.objects.get(name=category_name)
                queryset = queryset.filter(category=category)
            except Category.DoesNotExist:
                # 如果没有找到该分类，可以返回一个空查询集或其他处理
                queryset = Product.objects.none()
        # 获取最小价格
        queryset = queryset.annotate(min_price=Min('productsupplier__price'))
    
       # 价格区间筛选 (通过 ProductSupplier)
        min_price = self.request.GET.get('min_price')
        if min_price:
            queryset = queryset.filter(productsupplier__price__gte=min_price)

        max_price = self.request.GET.get('max_price')
        if max_price:
            queryset = queryset.filter(productsupplier__price__lte=max_price)

        # 只显示有折扣的商品
        discounted = self.request.GET.get('discounted')
        if discounted == 'true':
            queryset = queryset.filter(
                Q(discount__isnull=False) &
                Q(discount__valid_until__gte=timezone.now())  # 确保折扣仍然有效
            )

        # 排序
        sort = self.request.GET.get('sort')
        if sort == 'price_asc':
            queryset = queryset.order_by('min_price')
        elif sort == 'price_desc':
            queryset = queryset.order_by('-min_price')
        elif sort == 'discount':
            # 按折扣值排序，使用 discount__value 获取折扣的值
            queryset = queryset.filter(
                Q(discount__isnull=False) &
                Q(discount__valid_until__gte=timezone.now())  # 确保折扣仍然有效
            )            
            queryset = queryset.annotate(discount_value=F('discount__value')).order_by('-discount_value')
        elif sort == 'expiry':
            # 只对有折扣的商品进行排序，过滤没有折扣的商品
            queryset = queryset.filter(
                Q(discount__isnull=False) &
                Q(discount__valid_until__gte=timezone.now())  # 确保折扣仍然有效
            )            
            queryset = queryset.annotate(discount_expiry=F('discount__valid_until')).order_by('discount_expiry')  # 按折扣的有效期排序
        elif sort == 'comprehensive':
            # 不做任何筛选，直接返回所有产品
            queryset = Product.objects.all()   

        return queryset.distinct()

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'category']
    permission_classes = [IsVendorOrAdmin]

    def perform_create(self, serializer):
        if self.request.user.is_vendor:
            supplier = Supplier.objects.get(user=self.request.user)
            product = serializer.save()
            product.supplier.add(supplier)  # 仅绑定 M2M，无需重复创建折扣

        # 如果请求中有 discount 字段，则创建并关联折扣
        discount_data = self.request.data.get('discount')
        if discount_data:
            Discount.objects.create(
                product=product,
                supplier=supplier,
                type=discount_data.get('type'),
                value=discount_data.get('value'),
                valid_from=discount_data.get('valid_from'),
                valid_until=discount_data.get('valid_until'),
            )
        else:
            raise PermissionDenied("You are not authorized to create products.")
        
    def perform_update(self, serializer):
        if self.request.user.is_vendor:
            product = self.get_object()
            supplier = Supplier.objects.get(user=self.request.user)

            # 确保供应商是当前产品的供应商
            product_supplier = ProductSupplier.objects.filter(product=product, supplier=supplier).first()
            if not product_supplier:
                raise PermissionDenied("You are not authorized to update the price for this product.")

            # 先执行保存，让 category、name、description 等字段更新
            updated_product = serializer.save()

           # 图片删除（image=null 或 ""）
            if 'image' in self.request.data and not self.request.data['image']:
                if updated_product.image:
                    updated_product.image.delete(save=False)
                    updated_product.image = None
                    updated_product.save()

            # 更新价格
            new_price = serializer.validated_data.get('price')
            if new_price is not None:
                product_supplier.price = new_price
                product_supplier.save()

            # 更新折扣（如果有）
            discount_data = self.request.data.get('discount')
            if discount_data:
                discount, created = Discount.objects.get_or_create(
                    product=product,
                    supplier=supplier,
                    defaults={
                        'type': discount_data.get('type', 'percentage'),
                        'value': discount_data.get('value', 0),
                        'valid_from': discount_data.get('valid_from'),
                        'valid_until': discount_data.get('valid_until'),
                    }
                )
                if not created:
                    discount.type = discount_data.get('type', discount.type)
                    discount.value = discount_data.get('value', discount.value)
                    discount.valid_from = discount_data.get('valid_from', discount.valid_from)
                    discount.valid_until = discount_data.get('valid_until', discount.valid_until)
                    discount.save()
        else:
            raise PermissionDenied("You are not authorized to update products.")

    def perform_destroy(self, instance):
        # 只有供应商或管理员才能删除产品
        if self.request.user.is_vendor or self.request.user.is_staff:
             # 删除图片文件（可选）
            if instance.image:
                instance.image.delete(save=False)
            instance.delete()
        else:
            raise PermissionDenied("You are not authorized to delete products.")
        
class ProductSupplierViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSupplierSerializer
    permission_classes = [permissions.IsAuthenticated, IsVendor]

    def get_queryset(self):
        # 只返回当前供应商相关的记录
        return ProductSupplier.objects.filter(supplier__user=self.request.user)

    def perform_create(self, serializer):
        supplier = Supplier.objects.get(user=self.request.user)
        serializer.save(supplier=supplier)

class DiscountViewSet(viewsets.ModelViewSet):
    serializer_class = DiscountSerializer
    queryset = Discount.objects.all()

    # 只允许供应商更新和删除自己的折扣
    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and hasattr(user, 'supplier'):
            # 供应商只能看到他们自己的折扣
            return Discount.objects.filter(supplier__user=user)
        return Discount.objects.none()

    def perform_update(self, serializer):
        discount = self.get_object()
        
        # 确保只有供应商可以更新他们自己的折扣
        if discount.supplier.user != self.request.user:
            raise PermissionError("您没有权限更新此折扣")

        # 保存更新
        serializer.save()

    def update(self, request, *args, **kwargs):
        # 在这里可以做额外的权限验证等操作
        try:
            return super().update(request, *args, **kwargs)
        except PermissionError as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
    
    def perform_destroy(self, instance):
        if instance.supplier.user != self.request.user:
            raise PermissionDenied("You are not authorized to delete this discount.")
        instance.delete()

class ShoppingListViewSet(viewsets.ModelViewSet):
    queryset = ShoppingList.objects.all()
    serializer_class = ShoppingListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return ShoppingList.objects.filter(
            models.Q(owner=user) | models.Q(shared_with=user)
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'], url_path='share')
    def share_list(self, request, pk=None):
        try:
            shopping_list = self.get_object()
        except ShoppingList.DoesNotExist:
            return Response({'detail': 'Shopping list not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        if shopping_list.owner != request.user:
            return Response({'detail': 'Only the owner can share this list.'}, status=status.HTTP_403_FORBIDDEN)
# 验证用户是否存在
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'detail': 'user_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            contact_user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        # 验证是否是联系人才可以共享
        if not Contact.objects.filter(user=request.user, contact_user=contact_user).exists():
            return Response({'detail': 'This user is not in your contact list.'}, status=status.HTTP_403_FORBIDDEN)

        # 添加共享用户
        shopping_list.shared_with.add(contact_user)
        shopping_list.save()

        return Response({'detail': f'{contact_user.username} added to shared list.'}, status=status.HTTP_200_OK)


class ShoppingItemViewSet(viewsets.ModelViewSet):
    queryset = ShoppingItem.objects.all()
    serializer_class = ShoppingItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = ShoppingItem.objects.filter(list__owner=self.request.user)
        expiring_soon = self.request.query_params.get('expiring_soon')
        if expiring_soon:
            today = timezone.now().date()
            soon_date = today + timedelta(days=3)
            queryset = queryset.filter(expiration_date__lte=soon_date, expiration_date__gte=today)
        return queryset
    
    @action(detail=True, methods=['post'], url_path='mark-as-purchased')
    def mark_as_purchased(self, request, pk=None):
        try:
            shopping_item = self.get_object()
        except ShoppingItem.DoesNotExist:
            return Response({'detail': 'Shopping item not found.'}, status=status.HTTP_404_NOT_FOUND)

        if shopping_item.is_checked:
            return Response({'detail': 'This item has already been marked as purchased.'}, status=status.HTTP_400_BAD_REQUEST)

        shopping_item.add_to_fridge()
        return Response({'detail': 'Item marked as purchased and added to fridge.'}, status=status.HTTP_200_OK)

class FridgeViewSet(viewsets.ModelViewSet):
    queryset = ShoppingItem.objects.filter(is_checked=True)
    serializer_class = ShoppingItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return ShoppingItem.objects.filter(list__owner=user, is_checked=True)

class SharedShoppingListView(APIView):
    def get(self, request, uuid):
        try:
            shopping_list = ShoppingList.objects.get(uuid=uuid, is_shared=True)
            serializer = ShoppingListSerializer(shopping_list)
            return Response(serializer.data)
        except ShoppingList.DoesNotExist:
            return Response({"detail": "List not found or not shared."}, status=status.HTTP_404_NOT_FOUND)

class ShoppingListsSharedWithMeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # 获取当前登录的用户
        user = request.user
        
        # 获取该用户被共享的购物清单
        shared_lists = ShoppingList.objects.filter(shared_with=user)
        
        # 序列化数据
        serializer = ShoppingListSerializer(shared_lists, many=True)
        
        return Response(serializer.data)


class AddProductToShoppingListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, shopping_list_id, product_id):
        try:
            shopping_list = ShoppingList.objects.get(id=shopping_list_id, owner=request.user)
            product = Product.objects.get(id=product_id)
            quantity = request.data.get('quantity', 1)  # 获取请求中的数量，默认为1

            # 查找该商品在所有供应商中的最低价格
            product_suppliers = ProductSupplier.objects.filter(product=product)
            if not product_suppliers.exists():
                return Response({"detail": "No suppliers found for this product."}, status=status.HTTP_404_NOT_FOUND)

            lowest_price_supplier = product_suppliers.order_by('price').first()
            price_per_unit = lowest_price_supplier.price
            now = datetime.now()

            discount = Discount.objects.filter(
                supplier=lowest_price_supplier.supplier,
                product=product,
                valid_from__lte=now,
                valid_until__gte=now
            ).first()

            if discount:
                if discount.type == 'percentage':
                    total_price = price_per_unit * quantity * (1 - discount.value / 100)
                elif discount.type == 'fixed':
                    total_price = price_per_unit * quantity - discount.value
                else:
                    total_price = price_per_unit * quantity
            else:
                total_price = price_per_unit * quantity

            supplier = lowest_price_supplier.supplier.user.username 

            # 将商品添加到购物清单中（按原有数量追加）
            shopping_item, created = ShoppingItem.objects.get_or_create(
                list=shopping_list,
                product=product,
                defaults={
                    'quantity': quantity,
                    'is_checked': False,
                    'total_price': total_price  # 添加总价格字段
                }
            )

            if not created:
                shopping_item.quantity += int(quantity)
                if discount:
                    if discount.type == 'percentage':
                        shopping_item.total_price = price_per_unit * shopping_item.quantity * (1 - discount.value / 100)
                    elif discount.type == 'fixed':
                        shopping_item.total_price = price_per_unit * shopping_item.quantity - discount.value
                    else:
                        shopping_item.total_price = price_per_unit * shopping_item.quantity
                else:
                    shopping_item.total_price = price_per_unit * shopping_item.quantity

                shopping_item.save()


            return Response({
                'status': 'product added to shopping list',
                'product_name': product.name,
                'quantity': quantity,
                'total_price': total_price,  # 返回总价格
                'supplier': supplier,
            })
        except ShoppingList.DoesNotExist:
            return Response({"detail": "Shopping list not found."}, status=status.HTTP_404_NOT_FOUND)
        except Product.DoesNotExist:
            return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

class MarkItemAsPurchasedView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, item_id):
        try:
            item = ShoppingItem.objects.get(id=item_id, list__owner=request.user)
            expiration_date = request.data.get("expiration_date")

            if not expiration_date:
                return Response({"detail": "Expiration date is required."}, status=400)

            item.is_checked = True
            item.expiration_date = expiration_date
            item.save()

            return Response({"status": "Item marked as purchased."})
        except ShoppingItem.DoesNotExist:
            return Response({"detail": "Item not found."}, status=404)

#还没过期，但快要过期的商品
class ExpiringProductsView(viewsets.ModelViewSet):
    serializer_class = ShoppingItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        today = timezone.now().date()
        soon = today + timedelta(days=3)
        return ShoppingItem.objects.filter(
            list__owner=self.request.user,
            expiration_date__range=(today, soon),
            reminder_sent=False
        )
    
#已经过期的商品
class ExpiredProductsView(viewsets.ModelViewSet):
    serializer_class = ShoppingItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        today = timezone.now().date()
        return ShoppingItem.objects.filter(
            list__owner=self.request.user,
            expiration_date__lt=today
        )
        
class MarkAllExpiredAsReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        today = timezone.now().date()

        # 过滤所有“过期且未提醒”的项目
        expired_items = ShoppingItem.objects.filter(
            list__owner=user,
            expiration_date__lt=today,
            reminder_sent=False
        )

        count = expired_items.count()
        expired_items.update(reminder_sent=True)

        return Response({"message": f"{count} expired items marked as read."})

class MarkAllExpiringAsReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]


    def post(self, request):
        user = request.user
        today = timezone.now().date()
        soon = today + timedelta(days=3)  # 快过期的商品是 3 天内的

        # 过滤所有“快过期且未提醒”的商品
        expiring_items = ShoppingItem.objects.filter(
            list__owner=user,
            expiration_date__range=(today, soon),
            reminder_sent=False
        )

        count = expiring_items.count()
        expiring_items.update(reminder_sent=True)

        return Response({"message": f"{count} expiring items marked as read."})

#根据用户购买过的产品找出常买的category，再推荐这个类别下的产品 + 当前有折扣的商品。
class RecommendationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        # 1. 获取用户购买过的产品类别
        items = ShoppingItem.objects.filter(list__owner=user)
        category_counts = (
            items
            .values('product__category')
            .annotate(count=Count('product'))
            .order_by('-count')
        )

        if not category_counts:
            return Response({"message": "No purchase history yet."})

        top_category = category_counts[0]['product__category']

        # 2. 推荐这个分类下的产品（排除用户已购买的）
        purchased_product_ids = items.values_list('product__id', flat=True)
        recommended_products = Product.objects.filter(
            category=top_category
        ).exclude(id__in=purchased_product_ids)

        # 3. 推荐当前正在打折的商品
        now = timezone.now()
        discounted_products = Product.objects.filter(
            discount__valid_from__lte=now,
            discount__valid_until__gte=now
        ).distinct()

        # 序列化输出
        rec_products_serialized = ProductSerializer(recommended_products, many=True).data
        discount_products_serialized = ProductSerializer(discounted_products, many=True).data

        return Response({
            "category_based_recommendations": rec_products_serialized,
            "discounted_products": discount_products_serialized
        })
    

class DiscountsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Discount.objects.all()
    serializer_class = DiscountSerializer
