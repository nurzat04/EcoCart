import os
from rest_framework import status, generics,permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import Contact
from .serializers import ContactSerializer, UserSerializer, EmailLoginSerializer, UserAvatarSerializer
from django.contrib.auth import get_user_model
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.core.mail import send_mail
from shopping.models import ShoppingList
from shopping.serializers import ShoppingListSerializer
from django.contrib.auth.tokens import default_token_generator
from google.oauth2 import id_token
from google.auth.transport import requests
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.db.models import Q

User = get_user_model()

class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class UploadAvatarView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

    def put(self, request, *args, **kwargs):
        serializer = UserAvatarSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': '头像上传成功', 'image': serializer.data['image']})
        
        return Response(serializer.errors, status=400)
    
class UserShoppingListView(generics.ListAPIView):
    serializer_class = ShoppingListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        return ShoppingList.objects.filter(owner=user_id)
    
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # 获取请求数据
        data = request.data.copy()

        # 确保密码字段存在
        if not data.get("password"):
            return Response({"error": "Password is required."}, status=status.HTTP_400_BAD_REQUEST)

        # 强制注册用户身份为普通客户
        data["is_vendor"] = False
        data["is_admin"] = False

        # 使用UserSerializer进行数据验证和保存
        serializer = UserSerializer(data=data)
        if serializer.is_valid():
            user = serializer.save()

            # 生成 JWT token
            refresh = RefreshToken.for_user(user)
            return Response({
                "message": "Customer registered successfully.",
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "is_vendor": user.is_vendor,
                "is_admin": user.is_admin,
                "image": user.image.url if user.image else None,
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    def post(self, request):
        serializer = EmailLoginSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class GoogleLoginView(APIView):
    def post(self, request):
        token = request.data.get("id_token")
        if not token:
            return Response({"error": "缺少 id_token"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            idinfo = id_token.verify_oauth2_token(token, requests.Request(), "YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com")
            email = idinfo["email"]
            name = idinfo.get("name", "")

            user, created = User.objects.get_or_create(email=email, defaults={"username": email})
            return Response({
                "message": "登录成功",
                "user": {
                    "id": user.id,
                    "email": user.email,
                }
            })
        except ValueError:
            return Response({"error": "无效的 Google token"}, status=status.HTTP_400_BAD_REQUEST)


class RequestPasswordResetView(APIView):
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email is required'}, status=400)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)

        token = default_token_generator.make_token(user)
        uid = user.pk

        reset_url = f"https://ecocartapp.com/reset-password?token={token}&uid={uid}"

        # 示例邮件发送
        send_mail(
            subject="Reset your password",
            message=f"Click the link to reset your password:\n{reset_url}",
            from_email="noreply@yourapp.com",
            recipient_list=[user.email],
        )

        return Response({
            'message': 'Reset link sent',
            'token': token,
            'uid': uid,
        })

class ResetPasswordConfirmView(APIView):
    def post(self, request):
        token = request.data.get('token')
        uid = request.data.get('uid')
        password = request.data.get('password')

        if not token or not uid or not password:
            return Response({'error': 'All fields required'}, status=400)

        try:
            user = User.objects.get(pk=uid)
        except User.DoesNotExist:
            return Response({'error': 'Invalid user'}, status=404)

        if not default_token_generator.check_token(user, token):
            return Response({'error': 'Invalid or expired token'}, status=400)

        user.set_password(password)
        user.save()

        return Response({'message': 'Password has been reset successfully'})


class AddContactView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        username = request.data.get('username')
        note = request.data.get('note', '')

        if not username:
            return Response({"error": "Username is required"}, status=status.HTTP_400_BAD_REQUEST)

        contact_user = get_object_or_404(User, username__iexact=username)

        if contact_user == request.user:
            return Response({"error": "You cannot add yourself"}, status=status.HTTP_400_BAD_REQUEST)

        contact, created = Contact.objects.get_or_create(user=request.user, contact_user=contact_user)
        contact.note = note
        contact.save()

        if created:
            return Response({"message": f"{username} added successfully"}, status=status.HTTP_201_CREATED)
        return Response({"message": f"{username} is already in your contact list. Note updated."}, status=status.HTTP_200_OK)

class ContactListView(generics.ListAPIView):
    serializer_class = ContactSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Contact.objects.filter(user=self.request.user)
    
class ContactUpdateView(generics.UpdateAPIView):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # 获取当前登录用户的联系人
        return Contact.objects.get(user=self.request.user, id=self.kwargs['contact_id'])

    def patch(self, request, *args, **kwargs):
        contact = self.get_object()
        # 只允许更新备注
        contact.note = request.data.get('note', contact.note)
        contact.save()
        return self.update(request, *args, **kwargs)
    
class DeleteContactView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, contact_id):
        contact = get_object_or_404(Contact, id=contact_id, user=request.user)
        contact.delete()
        return Response({"message": f"Contact with ID {contact_id} removed"}, status=status.HTTP_204_NO_CONTENT)
        

class UserSearchView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        query = self.request.query_params.get('q', '')
        return User.objects.filter(Q(username__icontains=query)).exclude(id=self.request.user.id)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
