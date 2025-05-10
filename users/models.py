from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    is_vendor = models.BooleanField(default=False)  # 是否是供应商
    is_admin = models.BooleanField(default=False)  # 是否是管理员
    image = models.ImageField(upload_to='user_images/', null=True, blank=True)
    fcm_token = models.CharField(max_length=255, null=True, blank=True)
    
    def __str__(self):
        return self.username

class Contact(models.Model):
    user = models.ForeignKey(CustomUser, related_name='contacts', on_delete=models.CASCADE)
    contact_user = models.ForeignKey(CustomUser, related_name='contacted_by', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        unique_together = ('user', 'contact_user')  # 防止重复添加

    def __str__(self):
        return f"{self.user.username} -> {self.contact_user.username}"
