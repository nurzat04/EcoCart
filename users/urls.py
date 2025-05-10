from django.urls import path
from .views import AddContactView, ContactListView, ContactUpdateView, DeleteContactView, RegisterView, LoginView,  UserListView, UserSearchView, UserShoppingListView, GoogleLoginView, RequestPasswordResetView, ResetPasswordConfirmView, UploadAvatarView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('google-login/', GoogleLoginView.as_view(), name='google_login'),    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/<int:user_id>/shopping_lists/', UserShoppingListView.as_view(), name='user-shopping-lists'),
    path("request-password-reset/", RequestPasswordResetView.as_view()),
    path("reset-password/", ResetPasswordConfirmView.as_view()),
    path('upload-avatar/', UploadAvatarView.as_view(), name='upload-avatar'),
    path('contacts/add/', AddContactView.as_view(), name='add-contact'),
    path('contacts/', ContactListView.as_view(), name='contact-list'),
    path('contacts/delete/<int:contact_id>/', DeleteContactView.as_view(), name='delete-contact'),
    path('users/search/', UserSearchView.as_view(), name='user-search'),
    path('contacts/update/<int:contact_id>/', ContactUpdateView.as_view(), name='update-contact')
]
