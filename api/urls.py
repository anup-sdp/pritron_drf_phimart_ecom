# api, urls.py:
from django.urls import path, include
from products.views import ProductViewSet, CategoryViewSet, ReviewViewSet, ProductImageViewSet
from orders.views import CartViewSet, CartItemViewSet, OrderViewset, initiate_payment
#from rest_framework.routers import DefaultRouter  # now using nested
from rest_framework_nested import routers  # simplifies the creation of nested API routes and views. 
from api.auth_views import CustomTokenObtainPairView

router = routers.DefaultRouter()
router.register('products', ProductViewSet, basename='products')
router.register('categories', CategoryViewSet) # basename ?
router.register('carts', CartViewSet, basename='carts')
router.register('orders', OrderViewset, basename='orders')

product_router = routers.NestedDefaultRouter(router, 'products', lookup='product') # lookup='product' 'cause: class Review/ProductImage has product field
product_router.register('reviews', ReviewViewSet, basename='product-review')
product_router.register('images', ProductImageViewSet, basename='product-images') # http://127.0.0.1:8000/api/products/1/images

cart_router = routers.NestedDefaultRouter(router, 'carts', lookup='cart')
cart_router.register('items', CartItemViewSet, basename='cart-item')  # 

# urlpatterns = router.urls

urlpatterns = [
    path('', include(router.urls)),
    path('', include(product_router.urls)),
    path('', include(cart_router.urls)),
	path('products2/', include('products.product_urls')), 
	path('categories2/', include('products.category_urls')),
    path('auth/', include('djoser.urls')), # Djoser core (registration, activation, password reset, etc.)
	# Override the JWT creation endpoint with our custom view
    # path('auth/jwt/create/', CustomTokenObtainPairView.as_view(), name='jwt_create'), 
    path('auth/', include('djoser.urls.jwt')), # Djoser + JWT
	path('payment/initiate/', initiate_payment, name='initiate-payment'),
]

"""
POST /api/auth/users/ → create user (inactive) + send activation email
GET /api/auth/users/activation/?uid=<uid>&token=<token> → activate
"""

# djoser.urls is changing initial page  Api Root from (http://127.0.0.1:8000/api/) to (http://127.0.0.1:8000/api/auth/) , sol: use  api/v1/  ?
# GET/POST: http://127.0.0.1:8000/api/auth/users
# http://127.0.0.1:8000/api/auth/users/me/

# pip install drf-nested-routers
# https://github.com/alanjds/drf-nested-routers

"""
http://127.0.0.1:8000/api/carts/

"""

# http://127.0.0.1:8000/api/products/1/
# http://127.0.0.1:8000/api/products/1/reviews/

"""
carts:
http://127.0.0.1:8000/api/carts/

{
    "detail": "Method \"GET\" not allowed."
}
-- bacause all cart list is not provided.

post: create cart of current user (admin@example.com-pw:1234)
HTTP 201 Created
Allow: POST, OPTIONS
Content-Type: application/json
Vary: Accept

{
    "id": "a3684336-c71e-40c8-a1fb-a92a30d8f7cd",
    "user": 1,
    "items": [],
    "total_price": 0
}

post: create cart of current user (anup@example.com-pw:aB@12345)
HTTP 201 Created
Allow: POST, OPTIONS
Content-Type: application/json
Vary: Accept

{
    "id": "773036c2-4e52-4471-b856-699acf401b13",
    "user": 2,
    "items": [],
    "total_price": 0
}
------------
visit http://127.0.0.1:8000/api/carts/773036c2-4e52-4471-b856-699acf401b13 while logged in as anup@example.com:
HTTP 200 OK
Allow: GET, DELETE, HEAD, OPTIONS
Content-Type: application/json
Vary: Accept

{
    "id": "773036c2-4e52-4471-b856-699acf401b13",
    "user": 2,
    "items": [],
    "total_price": 0
}
-------------------------
visit http://127.0.0.1:8000/api/carts/773036c2-4e52-4471-b856-699acf401b13/items to add a product to cart with "product_id" & "quantity" in post. (nested router)
^ can delete also, module 22.4-5
visit http://127.0.0.1:8000/api/carts/773036c2-4e52-4471-b856-699acf401b13/items/1/ to edit patch ----- how the /1 works -- url config where ?
# ^ the nested router defines and handles both the /items/ and /items/{pk}/ URLs automatically
"""