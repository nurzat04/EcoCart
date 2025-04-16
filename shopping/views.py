from rest_framework import viewsets, permissions, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import ShoppingList, ShoppingItem, Product, ProductSupplier, Supplier
from .serializers import ShoppingListSerializer, ShoppingItemSerializer, ProductSerializer, ProductSupplierSerializer, SupplierSerializer
from users.permissions import IsVendorOrAdmin, IsVendor
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count
from django.utils import timezone


class SupplierListView(viewsets.ReadOnlyModelViewSet):
    queryset = Supplier.objects.select_related('user').filter(user__is_vendor=True)
    serializer_class = SupplierSerializer


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'category']
    permission_classes = [IsVendorOrAdmin]

    def perform_create(self, serializer):
        if self.request.user.is_vendor:
            supplier = Supplier.objects.get(user=self.request.user)
            
            # 保存产品并将供应商添加到产品的 ManyToManyField
            product = serializer.save()
            product.supplier.add(supplier)  # 这里将 supplier 添加到 ManyToManyField 中
        else:
            raise PermissionDenied("You are not authorized to create products.")  # 如果不是供应商，抛出权限错误

    def perform_update(self, serializer):
        if self.request.user.is_vendor:
            product = self.get_object()
            
            supplier = Supplier.objects.get(user=self.request.user)

            # 确保供应商是当前产品的供应商
            product_supplier = ProductSupplier.objects.filter(product=product, supplier=supplier).first()
            if not product_supplier:
                raise PermissionDenied("You are not authorized to update the price for this product.")
            
            # 更新价格
            new_price = serializer.validated_data.get('price')  # 假设价格字段名为 'price'
            if new_price:
                product_supplier.price = new_price
                product_supplier.save()

            print(f"ProductSupplier updated: {product_supplier.product.name}, {product_supplier.price}")
            
            serializer.save()
        else:
            raise PermissionDenied("You are not authorized to update products.")
        
    def perform_destroy(self, instance):
        # 只有供应商或管理员才能删除产品
        if self.request.user.is_vendor or self.request.user.is_staff:
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

class ShoppingListViewSet(viewsets.ModelViewSet):
    queryset = ShoppingList.objects.all()
    serializer_class = ShoppingListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # 用户拥有的或共享给他的列表
        return ShoppingList.objects.filter(owner=self.request.user).distinct()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


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


class SharedShoppingListView(APIView):
    def get(self, request, uuid):
        try:
            shopping_list = ShoppingList.objects.get(uuid=uuid, is_shared=True)
            serializer = ShoppingListSerializer(shopping_list)
            return Response(serializer.data)
        except ShoppingList.DoesNotExist:
            return Response({"detail": "List not found or not shared."}, status=status.HTTP_404_NOT_FOUND)


class RemoveProductFromShoppingListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, shopping_list_id, product_id):
        try:
            shopping_list = ShoppingList.objects.get(id=shopping_list_id, owner=request.user)
            shopping_item = ShoppingItem.objects.get(list=shopping_list, product_id=product_id)
            shopping_item.delete()  # 删除购物项
            return Response({"detail": "Product removed from shopping list."}, status=status.HTTP_204_NO_CONTENT)
        except ShoppingList.DoesNotExist:
            return Response({"detail": "Shopping list not found."}, status=status.HTTP_404_NOT_FOUND)
        except ShoppingItem.DoesNotExist:
            return Response({"detail": "Product not found in shopping list."}, status=status.HTTP_404_NOT_FOUND)


class ProductPriceComparisonView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, product_id):
        """
        比较不同供应商提供的商品价格，返回最低价格的商品及供应商信息。
        """
        product = Product.objects.get(id=product_id)
        product_suppliers = ProductSupplier.objects.filter(product=product)

        if not product_suppliers.exists():
            return Response({"detail": "No suppliers found for this product."}, status=status.HTTP_404_NOT_FOUND)

        # 找到最低价格的供应商
        lowest_price_supplier = min(product_suppliers, key=lambda ps: ps.price)
        lowest_price = lowest_price_supplier.price
        supplier = lowest_price_supplier.supplier.user.username

        return Response({
            'product': product.name,
            'lowest_price': lowest_price,
            'supplier': supplier,
        })


class AddProductToShoppingListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, shopping_list_id, product_id):
        try:
            shopping_list = ShoppingList.objects.get(id=shopping_list_id, owner=request.user)
            product = Product.objects.get(id=product_id)
            quantity = request.data.get('quantity', 1)  # 获取请求中的数量，默认为1
            expiration_date = request.data.get('expiration_date')  # 支持用户自定义过期时间

            # 查找该商品在所有供应商中的最低价格
            product_suppliers = ProductSupplier.objects.filter(product=product)
            if not product_suppliers.exists():
                return Response({"detail": "No suppliers found for this product."}, status=status.HTTP_404_NOT_FOUND)

            lowest_price_supplier = min(product_suppliers, key=lambda ps: ps.price)
            price = lowest_price_supplier.price
            supplier = lowest_price_supplier.supplier.user.username 

            #将商品添加到购物清单中
            shopping_item, created = ShoppingItem.objects.update_or_create(
                list=shopping_list,
                product=product,
                defaults={
                    'quantity': quantity,
                    'is_checked': False,
                    'expiration_date': expiration_date
                }
            )
            return Response({
                'status': 'product added to shopping list',
                'product_name': product.name,
                'quantity': quantity,
                'price': price,
                'supplier': supplier,
            })
        except ShoppingList.DoesNotExist:
            return Response({"detail": "Shopping list not found."}, status=status.HTTP_404_NOT_FOUND)
        except Product.DoesNotExist:
            return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)
        
#还没过期，但快要过期的商品
class ExpiringProductsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()
        soon = today + timedelta(days=3)
        items = ShoppingItem.objects.filter(
            list__owner=request.user,
            expiration_date__range=(today, soon),
            reminder_sent=False  # 只取还没提醒过的
        )
        serializer = ShoppingItemSerializer(items, many=True)
        return Response(serializer.data)
    
    
#已经过期的商品
class ExpiredProductView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()
        items = ShoppingItem.objects.filter(
            list__owner=request.user,
            expiration_date__lt=today
        )
        serializer = ShoppingItemSerializer(items, many=True)
        return Response(serializer.data)
    
    
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
    

