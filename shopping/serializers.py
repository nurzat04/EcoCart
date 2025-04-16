# shopping/serializers.py
from datetime import datetime
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import ShoppingList, ShoppingItem, Supplier, Product, ProductSupplier, Discount
from users.serializers import UserSerializer
User = get_user_model()


class SupplierSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Supplier
        fields = ['id', 'user', 'company_name']


class ProductSupplierSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.user.username', read_only=True)

    class Meta:
        model = ProductSupplier
        fields = ['id', 'product', 'supplier', 'supplier_name', 'price', 'stock_status']
        read_only_fields = ['supplier']  # supplier 由后端自动赋值


class SupplierInfoSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.user.username', read_only=True)
    discount = serializers.SerializerMethodField()
    final_price = serializers.SerializerMethodField()

    class Meta:
        model = ProductSupplier
        fields = ['supplier_name', 'price', 'stock_status', 'discount', 'final_price']

    def get_discount(self, obj):
        now = datetime.now()
        discount = Discount.objects.filter(
            supplier=obj.supplier,
            product=obj.product,
            valid_from__lte=now,
            valid_until__gte=now
        ).first()

        if discount:
            return {
                'type': discount.discount_type,
                'value': str(discount.discount_value),
                'valid_until': discount.valid_until
            }
        return None

    def get_final_price(self, obj):
        base_price = obj.price
        now = datetime.now()
        discount = Discount.objects.filter(
            supplier=obj.supplier,
            product=obj.product,
            valid_from__lte=now,
            valid_until__gte=now
        ).first()

        if not discount:
            return str(base_price)

        if discount.discount_type == 'percentage':
            final = base_price * (1 - discount.discount_value / 100)
        elif discount.discount_type == 'fixed':
            final = base_price - discount.discount_value
        else:
            final = base_price

        return str(round(final, 2))


class ProductSerializer(serializers.ModelSerializer):
    price = serializers.DecimalField(max_digits=10, decimal_places=2, write_only=True, required=False)
    stock_status = serializers.ChoiceField(
        choices=[('in_stock', 'In Stock'), ('out_of_stock', 'Out of Stock')],
        write_only=True,
        required=False
    )
    suppliers_info = SupplierInfoSerializer(source='productsupplier_set', many=True, read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'category', 'price', 'stock_status', 'suppliers_info']

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user

        # 获取当前供应商对象
        try:
            supplier = Supplier.objects.get(user=user)
        except Supplier.DoesNotExist:
            raise serializers.ValidationError("当前用户不是供应商")

        # 拿出额外字段
        price = validated_data.pop('price', None)
        stock_status = validated_data.pop('stock_status', 'in_stock')

        # 根据名称和分类查找是否已有该产品
        product, created = Product.objects.get_or_create(
            name=validated_data['name'],
            category=validated_data['category'],
            defaults={'description': validated_data.get('description', '')}
        )

        # 检查是否已经为该产品绑定过该供应商
        if ProductSupplier.objects.filter(product=product, supplier=supplier).exists():
            raise serializers.ValidationError("你已为该商品设置过价格，不能重复创建。")

        # 创建供应商绑定记录
        ProductSupplier.objects.create(
            product=product,
            supplier=supplier,
            price=price if price is not None else 0,
            stock_status=stock_status
        )

        return product
# Discount Serializer
class DiscountSerializer(serializers.ModelSerializer):
    supplier = SupplierSerializer()
    product = ProductSerializer()

    class Meta:
        model = Discount
        fields = ['id', 'supplier', 'product', 'discount_type', 'discount_value', 'valid_from', 'valid_until']

    
class ShoppingItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer() 
    class Meta:
        model = ShoppingItem
        fields = ['id', 'product', 'quantity', 'expiration_date', 'is_checked']
        

class ShoppingListSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    shared_with = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), many=True)
    items = ShoppingItemSerializer(many=True, read_only=True)  # 嵌套显示购物项

    class Meta:
        model = ShoppingList
        fields = ['id', 'name', 'owner', 'shared_with', 'created_at', 'uuid', 'is_shared', 'items']

# Product Price Comparison Serializer (用于显示价格比较结果)
class ProductPriceComparisonSerializer(serializers.Serializer):
    product = serializers.CharField()
    lowest_price_supplier = serializers.CharField()
    lowest_price = serializers.DecimalField(max_digits=10, decimal_places=2)

