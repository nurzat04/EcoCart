# urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, ShoppingListViewSet, ShoppingItemViewSet, SharedShoppingListView, ProductPriceComparisonView, AddProductToShoppingListView, RemoveProductFromShoppingListView, ProductSupplierViewSet, ExpiringProductsView, ExpiredProductView,SupplierListView,RecommendationView
from .views_admin import AdminDashboardView 

router = DefaultRouter()
router.register(r'products', ProductViewSet)  
router.register(r'suppliers', SupplierListView, basename='supplier')
router.register(r'lists', ShoppingListViewSet)
router.register(r'items', ShoppingItemViewSet)
router.register(r'product-supplier', ProductSupplierViewSet, basename='product-supplier')

urlpatterns = [
    path('', include(router.urls)),
    path('list/share/<uuid:uuid>/', SharedShoppingListView.as_view(), name='shared-shopping-list'),
    path('supplier-products/compare-prices/<int:product_id>/', ProductPriceComparisonView.as_view(), name='compare-product-prices'),
    path('shopping-lists/<int:shopping_list_id>/add-product/<int:product_id>/', AddProductToShoppingListView.as_view(), name='add-product-to-list'),
    path('shopping-lists/<int:shopping_list_id>/remove-product/<int:product_id>/', RemoveProductFromShoppingListView.as_view(), name='remove-product-from-list'), 
    path('admin/dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('shopping-items/expiring/', ExpiringProductsView.as_view(), name='expiring-products'),
    path('shopping-items/expired/', ExpiredProductView.as_view(), name='expiring-products'),
    path('recommendations/', RecommendationView.as_view(), name='recommended-products'),
]
