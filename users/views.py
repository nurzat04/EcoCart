import os
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserSerializer
from django.contrib.auth import get_user_model
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.core.mail import send_mail
from django.conf import settings
from shopping.models import ShoppingList
from shopping.serializers import ShoppingListSerializer
from shopping.models import Supplier
User = get_user_model()

class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class UserShoppingListView(generics.ListAPIView):
    serializer_class = ShoppingListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        return ShoppingList.objects.filter(owner=user_id)
    
class RegisterView(APIView):
    def post(self, request):
        # 检查请求中的 user_type 字段
        user_type = request.data.get('user_type', 'customer')  # 默认是普通用户
        if user_type not in ['vendor', 'admin', 'customer']:
            return Response({"error": "Invalid user type"}, status=status.HTTP_400_BAD_REQUEST)
        
        # 注册用户时处理用户类型
        data = request.data.copy()
        if user_type == 'vendor':
            data['is_vendor'] = True
            
        elif user_type == 'admin':
            data['is_admin'] = True
        
        # 通过序列化器创建用户
        serializer = UserSerializer(data=data)
        if serializer.is_valid():
            user = serializer.save()
            # 如果用户是 vendor 类型，创建 Supplier
            if user.is_vendor:
                Supplier.objects.create(user=user)
            return Response({"message": f"{user_type.capitalize()} registered successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
class LoginView(APIView):
    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(username=username, password=password)

        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            })
        return Response({"error": "Invalid Credentials"}, status=status.HTTP_401_UNAUTHORIZED)
    
class GoogleLogin(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        id_token_str = request.data.get('id_token')
        try:
            # 使用 Google 的公共密钥验证 ID Token
            id_info = id_token.verify_oauth2_token(id_token_str, Request(), os.getenv("GOOGLE_CLIENT_ID"))
            
            # 通过 id_info 获取用户信息，并在你的数据库中查找或创建用户
            user, created = User.objects.get_or_create(email=id_info['email'])
            
            # 如果用户是第一次通过 Google 登录，可能还需要填充其他信息，比如姓名
            if created:
                user.first_name = id_info.get('given_name', '')
                user.last_name = id_info.get('family_name', '')
                user.save()

            # 生成 JWT Token
            refresh = RefreshToken.for_user(user)
            
            # 发送电子邮件通知用户
            self.send_welcome_email(user.email)

            return Response({
                "message": "登录成功",
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            })
        except ValueError:
            return Response({"error": "无效的 ID Token"}, status=status.HTTP_400_BAD_REQUEST)

    def send_welcome_email(self, email):
        subject = "Welcome to the Ecocart"
        message = "感谢您使用 Google 登录，我们很高兴欢迎您加入 Ecocart！"
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])