from datetime import datetime
from django.db import models
from django.conf import settings
import uuid
from users.models import CustomUser

class Supplier(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='supplier_profile')
    company_name = models.CharField(max_length=255, blank=True, null=True)
    # 可以扩展更多字段，比如地址、电话、税号等

    def __str__(self):
        return self.user.username
   
class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)

    def __str__(self):
        return self.display_name

class Product(models.Model):
    name = models.CharField(max_length=255)
    # price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    supplier = models.ManyToManyField(Supplier, through='ProductSupplier')
    image = models.ImageField(upload_to='products/', null=True, blank=True)  
    
    def __str__(self):
        return self.name
    
    def get_discount(self):
        return Discount.objects.filter(product=self).first()


class ProductSupplier(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    stock_status = models.CharField(
        max_length=20,
        choices=[('in_stock', 'In Stock'), ('out_of_stock', 'Out of Stock')],
        default='in_stock'
    )

    def __str__(self):
        return f'{self.product.name} - {self.supplier.user.username}'


class Discount(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    type = models.CharField(max_length=50, choices=[('percentage', 'Percentage'), ('fixed', 'Fixed')])  # 折扣类型
    value = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # 折扣值
    valid_from = models.DateTimeField()  # 开始时间
    valid_until = models.DateTimeField()  # 结束时间
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="discounts")

    def __str__(self):
        return f'{self.product.name} - {self.value} off'


class ShoppingList(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_shopping_lists')  # 改为指向自定义用户模型
    shared_with = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='shared_shopping_lists')  # 改为指向自定义用户模型
    created_at = models.DateTimeField(auto_now_add=True)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    is_shared = models.BooleanField(default=False)  # 控制是否允许公开访问

    def __str__(self):
        return self.name


class ShoppingItem(models.Model):
    list = models.ForeignKey(ShoppingList, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    is_checked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expiration_date = models.DateField(null=True, blank=True)  # 过期日期字段
    reminder_sent = models.BooleanField(default=False)  # 是否已发送过期提醒
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def __str__(self):
        return self.product.name
        
    def is_expired(self):
        """ 检查商品是否过期 """
        if self.expiration_date and self.expiration_date < datetime.date.today():
            return True
        return False
    
    def send_expiration_reminder(self):
        """ 发送过期提醒通知 """
        if not self.reminder_sent:
            # 在这里，你可以添加发提醒消息的逻辑，比如使用 WebSocket 或者其他方式
            self.reminder_sent = True
            self.save()
            
    def add_to_fridge(self):
        """ 当用户标记为已购买时，添加到冰箱并设置过期日期 """
        self.is_checked = True
        self.expiration_date = datetime.date.today() + timedelta(days=7)  # 例如，设置7天后的过期日期
        self.save()

