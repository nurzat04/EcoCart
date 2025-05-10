from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import Contact

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    is_contact = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "first_name", "last_name", "is_vendor", "is_admin", "image", "is_contact"]
        extra_kwargs = {
            "password": {"write_only": True}
        }

    def create(self, validated_data):
        # 强制注册的用户身份为客户
        validated_data["is_vendor"] = False
        validated_data["is_admin"] = False
        user = User.objects.create_user(**validated_data)
        return user
    
    def get_is_contact(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Contact.objects.filter(user=request.user, contact_user=obj).exists()
        return False
    
class ContactSerializer(serializers.ModelSerializer):
    contact_user = UserSerializer(read_only=True)
    note = serializers.CharField(allow_blank=True, required=False)

    class Meta:
        model = Contact
        fields = ['id', 'contact_user', 'note', 'created_at']

class UserAvatarSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['image']

class EmailLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("用户不存在")

        if not user.check_password(password):
            raise serializers.ValidationError("密码错误")

        if not user.is_active:
            raise serializers.ValidationError("该账户已被禁用")

        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_vendor": user.is_vendor,
                "is_admin": user.is_admin,
                "image": user.image.url if user.image else None,
            }
        }
