from django_filters.rest_framework import FilterSet  # --- 'django_filters'
from products.models import Product


class ProductFilter(FilterSet):
    class Meta:
        model = Product
        fields = {
            'category_id': ['exact'],
            'price': ['gt', 'lt']
        }
        
# eg. http://127.0.0.1:8000/api/products/?category_id=1
