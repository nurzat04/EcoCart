from django.urls import path
from .views import GoogleLogin, RegisterView, LoginView, UserListView, UserShoppingListView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('auth/google/', GoogleLogin.as_view(), name='google-login'),
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/<int:user_id>/shopping_lists/', UserShoppingListView.as_view(), name='user-shopping-lists'),

]
