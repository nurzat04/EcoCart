from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    is_vendor = models.BooleanField(default=False)  # 是否是供应商
    is_admin = models.BooleanField(default=False)  # 是否是管理员

    def __str__(self):
        return self.username
