# products, product_urls.py:
from django.urls import path
from products import views

# urlpatterns = [
#     path('', views.ProductList.as_view(), name='product-list'),
#     path('<int:id>/', views.ProductDetails.as_view(), name='product-list'),
# ]

urlpatterns = [
	path('product-list/', views.view_products, name = 'product-list'),  # http://127.0.0.1:8000/api/products2/product-list/  --- test add
	path('<int:id>/', views.view_specific_product, name = 'specific_product'),  # http://127.0.0.1:8000/api/products2/1/
]