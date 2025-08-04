# orders, views.py:
from django.shortcuts import render
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin, DestroyModelMixin
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from orders import serializers as orderSz
from orders.serializers import CartSerializer, CartItemSerializer, AddCartItemSerializer, UpdateCartItemSerializer
from orders.models import Cart, CartItem, Order, OrderItem
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from orders.services import OrderService
from rest_framework.response import Response


class CartViewSet(CreateModelMixin, RetrieveModelMixin, DestroyModelMixin, GenericViewSet): # not ModelViewSet, not showing all carts list
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):  # if AnonymousUser
            return Cart.objects.none()
        return Cart.objects.prefetch_related('items__product').filter(user=self.request.user)  # prefetch_related used


class CartItemViewSet(ModelViewSet):
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AddCartItemSerializer
        elif self.request.method == 'PATCH':
            return UpdateCartItemSerializer
        return CartItemSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if getattr(self, 'swagger_fake_view', False): # ---
            return context

        return {'cart_id': self.kwargs.get('cart_pk')}

    def get_queryset(self):
        return CartItem.objects.select_related('product').filter(cart_id=self.kwargs.get('cart_pk'))  # select_related for forward ForeignKey or OneToOneField


class OrderViewset(ModelViewSet):
    http_method_names = ['get', 'post', 'delete', 'patch', 'head', 'options']

    @action(detail=True, methods=['post'])  # actions: https://www.django-rest-framework.org/api-guide/viewsets/#viewset-actions     
    def cancel(self, request, pk=None): # http://127.0.0.1:8000/api/orders/cfefff26-a539-4e91-918b-9caf5895d498/cancel
        order = self.get_object()
        OrderService.cancel_order(order=order, user=request.user)
        return Response({'status': 'Order canceled'})

    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None): # http://127.0.0.1:8000/api/orders/cfefff26-a539-4e91-918b-9caf5895d498/update_status
        order = self.get_object() # retrieves the specific Order instance based on the primary key (pk) in the URL
        serializer = orderSz.UpdateOrderSerializer(order, data=request.data, partial=True)  # notes below.     
        serializer.is_valid(raise_exception=True)
        serializer.save()  # commits changes to the database
        return Response({'status': f"Order status updated to {request.data['status']}"})

    def get_permissions(self):
        if self.action in ['update_status', 'destroy']:
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'cancel':
            return orderSz.EmptySerializer
        if self.action == 'create':
            return orderSz.CreateOrderSerializer
        elif self.action == 'update_status':
            return orderSz.UpdateOrderSerializer
        return orderSz.OrderSerializer

    def get_serializer_context(self):
        if getattr(self, 'swagger_fake_view', False):
            return super().get_serializer_context()
        return {'user_id': self.request.user.id, 'user': self.request.user}

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):  # if AnonymousUser
            return Order.objects.none()
        if self.request.user.is_staff:
            return Order.objects.prefetch_related('items__product').all()
        return Order.objects.prefetch_related('items__product').filter(user=self.request.user)


"""
# module 24.4
add items to cart:
http://127.0.0.1:8000/api/carts/a3684336-c71e-40c8-a1fb-a92a30d8f7cd/items/

then go to orders: http://127.0.0.1:8000/api/orders/
post the cart id to create order.
response:
HTTP 201 Created
Allow: GET, POST, HEAD, OPTIONS
Content-Type: application/json
Vary: Accept

{
    "id": "cfefff26-a539-4e91-918b-9caf5895d498",
    "user": 1,
    "status": "Not Paid",
    "total_price": 568.36,
    "created_at": "2025-07-28T19:45:11.540980Z",
    "items": [
        {
            "id": 1,
            "product": {
                "id": 1,
                "name": "Smartphone",
                "price": 213.8
            },
            "price": 213.8,
            "quantity": 2,
            "total_price": 427.6
        },
        {
            "id": 2,
            "product": {
                "id": 2,
                "name": "Laptop",
                "price": 46.92
            },
            "price": 46.92,
            "quantity": 3,
            "total_price": 140.76
        }
    ]
}

now can visit: http://127.0.0.1:8000/api/orders/cfefff26-a539-4e91-918b-9caf5895d498/
"""

# ***
"""
class OrderViewset > update_status method:
serializer = orderSz.UpdateOrderSerializer(order, data=request.data, partial=True)  
---
In Django REST Framework, when you instantiate a serializer you're really calling the base signature:

Serializer(instance=None, data=None, *, many=False, partial=False, context=None, ...)

Here's what each of those arguments means in your update_status action:

order: 
This is the first positional argument representing the existing model instance to be updated.
By passing your existing Order instance as the first (positional) argument, you're binding the serializer 
to that object. DRF now knows you intend to update this particular record rather than create a new one. 
Under the hood, when you later call serializer.save(), DRF will call your serializer's update() method 
(instead of create()) and hand it that same order instance.

data=request.data: 
contains the parsed data from the PATCH request body.
The data= keyword argument is how you hand the incoming payload (typically JSON) to the serializer 
for validation and eventual saving. In your case, request.data will contain something like:
{
  "status": "Shipped"
}
DRF will run this through UpdateOrderSerializer's field definitions and validators.

partial=True
This enables partial updates, meaning only fields included in the request data will be updated.
By default, a serializer in update mode will require that all fields declared on it be present in the input. 
Setting partial=True tells DRF “it's okay if only some of the fields are provided—just update the ones you got.” 
In your UpdateOrderSerializer you only have one field (status), but in other cases you might have multiple fields 
and only want to change one or two of them.
"""