# urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FridgeViewSet, MarkAllExpiredAsReadView, MarkAllExpiringAsReadView, MarkItemAsPurchasedView, ProductViewSet, ShoppingListViewSet, ShoppingItemViewSet, SharedShoppingListView,AddProductToShoppingListView,ProductSupplierViewSet, ExpiringProductsView, ExpiredProductsView, ShoppingListsSharedWithMeView,SupplierListView,RecommendationView, ProductListView, CategoryViewSet, DiscountViewSet, DiscountsViewSet
from .views_admin import AdminDashboardView 

router = DefaultRouter()
router.register(r'products', ProductViewSet)  
router.register(r'suppliers', SupplierListView, basename='supplier')
router.register(r'lists', ShoppingListViewSet)  
router.register(r'items', ShoppingItemViewSet)
router.register(r'product-supplier', ProductSupplierViewSet, basename='product-supplier')
router.register(r'product-lists', ProductListView, basename='product-list')
router.register(r'categories', CategoryViewSet)
router.register(r'discounts', DiscountViewSet, basename='discounts')
router.register(r'discount-lists', DiscountsViewSet, basename='discount-lists')
router.register(r'expiring-items', ExpiringProductsView, basename='expiring-item')
router.register(r'expired-items', ExpiredProductsView, basename='expired-item')
router.register(r'fridge', FridgeViewSet, basename='fridge') 

urlpatterns = [
    path('', include(router.urls)),
    path('list/share/<uuid:uuid>/', SharedShoppingListView.as_view(), name='shared-shopping-list'),
    path('shopping-lists/<int:shopping_list_id>/add-product/<int:product_id>/', AddProductToShoppingListView.as_view(), name='add-product-to-list'),
    path('admin/dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('recommendations/', RecommendationView.as_view(), name='recommended-products'),
    path('expired/mark-all/', MarkAllExpiredAsReadView.as_view(), name='mark_all_expired_as_read'),
    path('expiring/mark-all/', MarkAllExpiringAsReadView.as_view(), name='mark_all_expiring_as_read'),
    path('shopping-lists/shared-with-me/', ShoppingListsSharedWithMeView.as_view(), name='shared-with-me'),
    path('shopping-items/<int:item_id>/mark-purchased/', MarkItemAsPurchasedView.as_view(), name='mark-item-as-purchased'),
]
