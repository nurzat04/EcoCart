# shopping/serializers.py
from datetime import datetime
from rest_framework import serializers
from django.contrib.auth import get_user_model

from users.models import Contact
from .models import ShoppingList, ShoppingItem, Supplier, Product, ProductSupplier, Discount, Category
from users.serializers import UserSerializer
User = get_user_model()


class SupplierSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Supplier
        fields = ['id', 'user', 'company_name']

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'display_name']

class DiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discount
        fields = ['id', 'product','supplier', 'type', 'value', 'valid_from', 'valid_until']
        read_only_fields = ['supplier', 'product']
        unique_together = ('product', 'supplier')
        
    def create(self, validated_data):
        user = self.context['request'].user
        supplier = getattr(user, 'supplier', None)
        if not supplier:
            raise serializers.ValidationError("当前用户不是供应商")
        validated_data['supplier'] = supplier
        return super().create(validated_data)


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
                'type': discount.type,
                'value': str(discount.value),
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

        if discount.type == 'percentage':
            final = base_price * (1 - discount.value / 100)
        elif discount.type == 'fixed':
            final = base_price - discount.value
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
    category = serializers.CharField()
    discount = DiscountSerializer(write_only=True, required=False)  # Allow discount data in create/update
    image = serializers.ImageField(required=False)
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'category', 'price', 'stock_status', 'suppliers_info', 'discount', 'image']

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user

        # Retrieve category or raise validation error if not found
        category_name = validated_data.pop('category')
        try:
            category = Category.objects.get(name=category_name)
        except Category.DoesNotExist:
            available = Category.objects.values_list('name', flat=True)
            raise serializers.ValidationError(f"分类 '{category_name}' 不存在。可用分类: {list(available)}")

        # Ensure the user is a supplier
        try:
            supplier = Supplier.objects.get(user=user)
        except Supplier.DoesNotExist:
            raise serializers.ValidationError("当前用户不是供应商")

        price = validated_data.pop('price', None)
        stock_status = validated_data.pop('stock_status', 'in_stock')

        # Create or get the product
        product, created = Product.objects.get_or_create(
            name=validated_data['name'],
            category=category,
            defaults={'description': validated_data.get('description', '')}
        )

        # Prevent duplicate supplier-product relationship
        if ProductSupplier.objects.filter(product=product, supplier=supplier).exists():
            raise serializers.ValidationError("你已为该商品设置过价格，不能重复创建。")

        # Create the supplier-product relationship
        product_supplier = ProductSupplier.objects.create(
            product=product,
            supplier=supplier,
            price=price if price is not None else 0,
            stock_status=stock_status
        )

        return product

    def update(self, instance, validated_data):
        request = self.context.get('request')
        user = request.user

        # Ensure the user is a supplier
        try:
            supplier = Supplier.objects.get(user=user)
        except Supplier.DoesNotExist:
            raise serializers.ValidationError("当前用户不是供应商")

        # Update the category and product details
        category_name = validated_data.pop('category', None)
        if category_name:
            try:
                category = Category.objects.get(name=category_name)
            except Category.DoesNotExist:
                available = Category.objects.values_list('name', flat=True)
                raise serializers.ValidationError(f"分类 '{category_name}' 不存在。可用分类: {list(available)}")
            instance.category = category

        # Check if the supplier is updating their own product's price and stock
        product_supplier = ProductSupplier.objects.get(product=instance, supplier=supplier)
        product_supplier.price = validated_data.pop('price', product_supplier.price)
        product_supplier.stock_status = validated_data.pop('stock_status', product_supplier.stock_status)
        product_supplier.save()

        # Update the product instance fields
        instance.name = validated_data.get('name', instance.name)
        instance.description = validated_data.get('description', instance.description)
        instance.image = validated_data.get('image', instance.image)

        instance.save()

        return instance



class ProductSupplierSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product',
        write_only=True
    )
    supplier_name = serializers.CharField(source='supplier.user.username', read_only=True)

    class Meta:
        model = ProductSupplier
        fields = [
            'id',
            'product',        # 返回完整的 Product 对象
            'product_id',     # 创建/更新时用 product_id
            'supplier',
            'supplier_name',
            'price',
            'stock_status'
        ]
        read_only_fields = ['supplier']

    
class ShoppingItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer() 
    class Meta:
        model = ShoppingItem
        fields = ['id', 'product', 'quantity', 'expiration_date', 'is_checked', 'total_price', 'reminder_sent']
    

class ShoppingListSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)
    shared_with = UserSerializer(many=True, read_only=True)
    shared_with_ids = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), many=True, write_only=True, source='shared_with'
    )
    items = ShoppingItemSerializer(many=True, read_only=True)

    class Meta:
        model = ShoppingList
        fields = ['id', 'name', 'owner', 'shared_with', 'shared_with_ids', 'created_at', 'uuid', 'is_shared', 'items']

    def validate_shared_with_ids(self, users):
        request_user = self.context['request'].user
        contact_ids = Contact.objects.filter(user=request_user).values_list('contact_user__id', flat=True)
        for user in users:
            if user.id not in contact_ids:
                raise serializers.ValidationError(f"{user.username} is not in your contact list.")
        return users

    def create(self, validated_data):
        shared_with = validated_data.pop('shared_with', [])
        validated_data.pop('owner', None)  # 确保 owner 不重复传

        shopping_list = ShoppingList.objects.create(owner=self.context['request'].user, **validated_data)
        shopping_list.shared_with.set(shared_with)
        return shopping_list



# Product Price Comparison Serializer (用于显示价格比较结果)
class ProductPriceComparisonSerializer(serializers.Serializer):
    product = serializers.CharField()
    lowest_price_supplier = serializers.CharField()
    lowest_price = serializers.DecimalField(max_digits=10, decimal_places=2)

