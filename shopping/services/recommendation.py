from collections import Counter
from shopping.models import ShoppingItem, Product

def get_user_preferred_categories(user):
    items = ShoppingItem.objects.filter(user=user).select_related('product__category')
    categories = [item.product.category for item in items if item.product.category]
    most_common = Counter(categories).most_common(3)
    return [cat for cat, _ in most_common]

def recommend_products_by_category(categories):
    return Product.objects.filter(category__in=categories).order_by('-popularity')[:10]

def recommend_discounted_products():
    return Product.objects.filter(discount__gt=0).order_by('-discount')[:10]

def get_recommendations_for_user(user):
    categories = get_user_preferred_categories(user)
    category_recs = recommend_products_by_category(categories)
    discount_recs = recommend_discounted_products()
    return category_recs, discount_recs
