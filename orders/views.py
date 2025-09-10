# orders, views.py:
from django.shortcuts import render
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin, DestroyModelMixin, ListModelMixin
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework.views import APIView
from orders import serializers as orderSz
from orders.serializers import CartSerializer, CartItemSerializer, AddCartItemSerializer, UpdateCartItemSerializer
from orders.models import Cart, CartItem, Order, OrderItem
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from orders.services import OrderService
from rest_framework.response import Response
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.decorators import api_view
from django.http import HttpResponseRedirect
from django.conf import settings as main_settings  # Aliasing for clarity
from sslcommerz_lib import SSLCOMMERZ 



class CartViewSet(CreateModelMixin, ListModelMixin, RetrieveModelMixin, DestroyModelMixin, GenericViewSet): # not ModelViewSet, not showing all carts list
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):  # if AnonymousUser
            return Cart.objects.none()
        return Cart.objects.prefetch_related('items__product').filter(user=self.request.user)  # prefetch_related used
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Cart.objects.none()
        return Cart.objects.prefetch_related('items__product').filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        # Use transaction + handle IntegrityError for safety against race conditions
        try:
            with transaction.atomic():
                cart, created = Cart.objects.get_or_create(user=request.user)
        except IntegrityError:
            # rare race: creation failed because another request created it simultaneously
            cart = Cart.objects.get(user=request.user)
            created = False

        serializer = self.get_serializer(cart)
        if created:
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])  # creates a GET /carts/my_cart/ endpoint that returns the current user's cart.
    def my_cart(self, request):
        try:
            cart = Cart.objects.get(user=request.user)
            serializer = self.get_serializer(cart)
            return Response(serializer.data)
        except Cart.DoesNotExist:
            return Response(status=404)

# getattr(object, attribute_name, default_value)
# default_value: (optional) value to return if the attribute doesn't exist — avoids AttributeError

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
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):  # if AnonymousUser
            return Order.objects.none()
        if self.request.user.is_staff:
            return Order.objects.select_related('user').prefetch_related('items__product').all()
        return Order.objects.select_related('user').prefetch_related('items__product').filter(user=self.request.user)



@api_view(['POST'])
def initiate_payment(request):
    user = request.user
    amount = request.data.get("amount")
    order_id= request.data.get("orderId")
    num_items = request.data.get("numItems")

    settings = { 'store_id': 'anupc68bfa8f415e23', 'store_pass': 'anupc68bfa8f415e23@ssl', 'issandbox': True } # info from my sandbox account email, use .env file if production.
    sslcz = SSLCOMMERZ(settings)
    post_body = {}
    post_body['total_amount'] = amount
    post_body['currency'] = "BDT"
    post_body['tran_id'] = f"txn_{order_id}"
    post_body['success_url'] = f"{main_settings.BACKEND_URL}/api/payment/success/"
    post_body['fail_url'] = f"{main_settings.BACKEND_URL}/api/payment/fail/"
    post_body['cancel_url'] = f"{main_settings.BACKEND_URL}/api/payment/cancel/"
    post_body['emi_option'] = 0
    post_body['cus_name'] = user.full_name
    post_body['cus_email'] = user.email
    post_body['cus_phone'] = user.phone_number
    post_body['cus_add1'] = user.address
    post_body['cus_city'] = "Dhaka"
    post_body['cus_country'] = "Bangladesh"
    post_body['shipping_method'] = "NO"
    post_body['multi_card_name'] = ""
    post_body['num_of_item'] = num_items
    post_body['product_name'] = "e-commerce product"
    post_body['product_category'] = "Various"
    post_body['product_profile'] = "general"

    response = sslcz.createSession(post_body) # API response
    # print('from initiate_payment function :', response)
    # return Response(response)  # post request at: http://127.0.0.1:8000/api/payment/initiate/  # "GatewayPageURL"
    if response.get('status') == 'SUCCESS':
        return Response({'payment_url': response["GatewayPageURL"]})
    return Response({'error':response["failedreason"]}, status=status.HTTP_400_BAD_REQUEST)
                     

@api_view(['POST'])
def payment_success(request):
    print("Inside success")
    order_id = request.data.get("tran_id").split('_')[1]
    order = Order.objects.get(id=order_id)
    order.status = "Ready To Ship"
    order.save()
    return HttpResponseRedirect(f"{main_settings.FRONTEND_URL}/dashboard/orders/")


@api_view(['POST'])
def payment_cancel(request):
    return HttpResponseRedirect(f"{main_settings.FRONTEND_URL}/dashboard/orders/")


@api_view(['POST'])
def payment_fail(request):
    print("Inside fail")
    return HttpResponseRedirect(f"{main_settings.FRONTEND_URL}/dashboard/orders/")


class HasOrderedProduct(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, product_id):
        user = request.user
        has_ordered = OrderItem.objects.filter(
            order__user=user, product_id=product_id).exists()
        return Response({"hasOrdered": has_ordered})

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

"""
post request at: http://127.0.0.1:8000/api/payment/initiate/
console print:
from initiate_payment function : {'status': 'SUCCESS', 'failedreason': '', 'sessionkey': '5F6E5AEA7C0496EA63C0150C43B0207F', 'gw': {'visa': 'city_visa,ebl_visa,visacard', 'master': 'city_master,ebl_master,mastercard', 'amex': 'city_amex,amexcard', 'othercards': 'qcash,fastcash', 'internetbanking': 'city,abbank,bankasia,ibbl,mtbl,tapnpay,eblsky,instapay,pmoney,woori,modhumoti,fsibl', 'mobilebanking': 'dbblmobilebanking,bkash,nagad,abbank,ibbl,tap,upay,okaywallet,cellfine,mcash'}, 'redirectGatewayURL': 'https://sandbox.sslcommerz.com/gwprocess/v4/bankgw/indexhtml.php?mamount=100.26&ssl_id=25090911115818LFRuUEZGgZ0sE&Q=REDIRECT&SESSIONKEY=5F6E5AEA7C0496EA63C0150C43B0207F&tran_type=success&cardname=', 'directPaymentURLBank': '', 'directPaymentURLCard': '', 'directPaymentURL': '', 'redirectGatewayURLFailed': '', 'GatewayPageURL': 'https://sandbox.sslcommerz.com/EasyCheckOut/testcde5f6e5aea7c0496ea63c0150c43b0207f', 'storeBanner': 'https://sandbox.sslcommerz.com/stores/logos/demoLogo.png', 'storeLogo': 'https://sandbox.sslcommerz.com/stores/logos/demoLogo.png', 'store_name': 'Demo', 'desc': [{'name': 'AMEX', 'type': 'amex', 'logo': 'https://sandbox.sslcommerz.com/gwprocess/v4/image/gw/amex.png', 'gw': 'amexcard', 'r_flag': '1', 'redirectGatewayURL': 'https://sandbox.sslcommerz.com/gwprocess/v4/bankgw/indexhtmlOTP.php?mamount=100.26&ssl_id=25090911115818LFRuUEZGgZ0sE&Q=REDIRECT&SESSIONKEY=5F6E5AEA7C0496EA63C0150C43B0207F&tran_type=success&cardname=amexcard'}, {'name': 'VISA', 'type': 'visa', 'logo': 'https://sandbox.sslcommerz.com/gwprocess/v4/image/gw/visa.png', 'gw': 'visacard', 'r_flag': '1', 'redirectGatewayURL': 'https://sandbox.sslcommerz.com/gwprocess/v4/bankgw/indexhtmlOTP.php?mamount=100.26&ssl_id=25090911115818LFRuUEZGgZ0sE&Q=REDIRECT&SESSIONKEY=5F6E5AEA7C0496EA63C0150C43B0207F&tran_type=success&cardname=visavard'}, {'name': 'MASTER', 'type': 'master', 'logo': 'https://sandbox.sslcommerz.com/gwprocess/v4/image/gw/master.png', 'gw': 'mastercard', 'r_flag': '1', 'redirectGatewayURL': 'https://sandbox.sslcommerz.com/gwprocess/v4/bankgw/indexhtmlOTP.php?mamount=100.26&ssl_id=25090911115818LFRuUEZGgZ0sE&Q=REDIRECT&SESSIONKEY=5F6E5AEA7C0496EA63C0150C43B0207F&tran_type=success&cardname=mastercard'}, {'name': 'AMEX-City Bank', 'type': 'amex', 'logo': 'https://sandbox.sslcommerz.com/gwprocess/v4/image/gw/amex.png', 'gw': 'city_amex', 'r_flag': '1', 'redirectGatewayURL': 'https://sandbox.sslcommerz.com/gwprocess/v4/bankgw/indexhtmlOTP.php?mamount=100.26&ssl_id=25090911115818LFRuUEZGgZ0sE&Q=REDIRECT&SESSIONKEY=5F6E5AEA7C0496EA63C0150C43B0207F&tran_type=success&cardname=city_amex'}, {'name': 'QCash', 'type': 'othercards', 'logo': 'https://sandbox.sslcommerz.com/gwprocess/v4/image/gw/qcash.png', 'gw': 'qcash', 'r_flag': '1', 'redirectGatewayURL': 'https://sandbox.sslcommerz.com/gwprocess/v4/bankgw/indexhtmlOTP.php?mamount=100.26&ssl_id=25090911115818LFRuUEZGgZ0sE&Q=REDIRECT&SESSIONKEY=5F6E5AEA7C0496EA63C0150C43B0207F&tran_type=success&cardname=qcash'}, {'name': 'Fast Cash', 'type': 'othercards', 'logo': 'https://sandbox.sslcommerz.com/gwprocess/v4/image/gw/fastcash.png', 'gw': 'fastcash'}, {'name': 'bKash', 'type': 'mobilebanking', 'logo': 'https://sandbox.sslcommerz.com/gwprocess/v4/image/gw/bkash.png', 'gw': 'bkash', 'r_flag': '1', 'redirectGatewayURL': 'https://sandbox.sslcommerz.com/gwprocess/v4/bankgw/indexhtmlOTP.php?mamount=100.26&ssl_id=25090911115818LFRuUEZGgZ0sE&Q=REDIRECT&SESSIONKEY=5F6E5AEA7C0496EA63C0150C43B0207F&tran_type=success&cardname=bkash'}, {'name': 'Nagad', 'type': 'mobilebanking', 'logo': 'https://sandbox.sslcommerz.com/gwprocess/v4/image/gw/nagad.png', 'gw': 'nagad', 'r_flag': '1', 'redirectGatewayURL': 'https://sandbox.sslcommerz.com/gwprocess/v4/bankgw/indexhtmlOTP.php?mamount=100.26&ssl_id=25090911115818LFRuUEZGgZ0sE&Q=REDIRECT&SESSIONKEY=5F6E5AEA7C0496EA63C0150C43B0207F&tran_type=success&cardname=nagad'}, {'name': 'DBBL Mobile Banking', 'type': 'mobilebanking', 'logo': 'https://sandbox.sslcommerz.com/gwprocess/v4/image/gw/dbblmobilebank.png', 'gw': 'dbblmobilebanking', 'r_flag': '1', 'redirectGatewayURL': 'https://sandbox.sslcommerz.com/gwprocess/v4/bankgw/indexhtmlOTP.php?mamount=100.26&ssl_id=25090911115818LFRuUEZGgZ0sE&Q=REDIRECT&SESSIONKEY=5F6E5AEA7C0496EA63C0150C43B0207F&tran_type=success&cardname=dbblmobilebanking'}, {'name': 'AB Direct', 'type': 'mobilebanking', 'logo': 'https://sandbox.sslcommerz.com/gwprocess/v4/image/gw/abbank.png', 'gw': 'abbank', 'r_flag': '1', 'redirectGatewayURL': 'https://sandbox.sslcommerz.com/gwprocess/v4/bankgw/indexhtmlOTP.php?mamount=100.26&ssl_id=25090911115818LFRuUEZGgZ0sE&Q=REDIRECT&SESSIONKEY=5F6E5AEA7C0496EA63C0150C43B0207F&tran_type=success&cardname=abbank'}, {'name': 'AB Direct', 'type': 'internetbanking', 'logo': 'https://sandbox.sslcommerz.com/gwprocess/v4/image/gw/abbank.png', 'gw': 'abbank', 'r_flag': '1', 'redirectGatewayURL': 'https://sandbox.sslcommerz.com/gwprocess/v4/bankgw/indexhtmlOTP.php?mamount=100.26&ssl_id=25090911115818LFRuUEZGgZ0sE&Q=REDIRECT&SESSIONKEY=5F6E5AEA7C0496EA63C0150C43B0207F&tran_type=success&cardname=abbank'}, {'name': 'IBBL', 'type': 'internetbanking', 'logo': 'https://sandbox.sslcommerz.com/gwprocess/v4/image/gw/ibbl.png', 'gw': 'ibbl', 'r_flag': '1', 'redirectGatewayURL': 'https://sandbox.sslcommerz.com/gwprocess/v4/bankgw/indexhtmlOTP.php?mamount=100.26&ssl_id=25090911115818LFRuUEZGgZ0sE&Q=REDIRECT&SESSIONKEY=5F6E5AEA7C0496EA63C0150C43B0207F&tran_type=success&cardname=ibbl'}, {'name': 'Citytouch', 'type': 'internetbanking', 'logo': 'https://sandbox.sslcommerz.com/gwprocess/v4/image/gw/citytouch.png', 'gw': 'city', 'r_flag': '1', 'redirectGatewayURL': 'https://sandbox.sslcommerz.com/gwprocess/v4/bankgw/indexhtmlOTP.php?mamount=100.26&ssl_id=25090911115818LFRuUEZGgZ0sE&Q=REDIRECT&SESSIONKEY=5F6E5AEA7C0496EA63C0150C43B0207F&tran_type=success&cardname=city'}, {'name': 'MTBL', 'type': 'internetbanking', 'logo': 'https://sandbox.sslcommerz.com/gwprocess/v4/image/gw/mtbl.png', 'gw': 'mtbl', 'r_flag': '1', 'redirectGatewayURL': 'https://sandbox.sslcommerz.com/gwprocess/v4/bankgw/indexhtmlOTP.php?mamount=100.26&ssl_id=25090911115818LFRuUEZGgZ0sE&Q=REDIRECT&SESSIONKEY=5F6E5AEA7C0496EA63C0150C43B0207F&tran_type=success&cardname=mtbl'}, {'name': 'Bank Asia', 'type': 'internetbanking', 'logo': 'https://sandbox.sslcommerz.com/gwprocess/v4/image/gw/bankasia.png', 'gw': 'bankasia', 'r_flag': '1', 'redirectGatewayURL': 'https://sandbox.sslcommerz.com/gwprocess/v4/bankgw/indexhtmlOTP.php?mamount=100.26&ssl_id=25090911115818LFRuUEZGgZ0sE&Q=REDIRECT&SESSIONKEY=5F6E5AEA7C0496EA63C0150C43B0207F&tran_type=success&cardname=bankasia'}, {'name': 'VISA-Eastern Bank Limited', 'type': 'visa', 'logo': 'https://sandbox.sslcommerz.com/gwprocess/v4/image/gw/visa.png', 'gw': 'ebl_visa', 'r_flag': '1', 'redirectGatewayURL': 'https://sandbox.sslcommerz.com/gwprocess/v4/bankgw/indexhtmlOTP.php?mamount=100.26&ssl_id=25090911115818LFRuUEZGgZ0sE&Q=REDIRECT&SESSIONKEY=5F6E5AEA7C0496EA63C0150C43B0207F&tran_type=success&cardname=ebl_visa'}, {'name': 'MASTER-Eastern Bank Limited', 'type': 'master', 'logo': 'https://sandbox.sslcommerz.com/gwprocess/v4/image/gw/master.png', 'gw': 'ebl_master', 'r_flag': '1', 'redirectGatewayURL': 'https://sandbox.sslcommerz.com/gwprocess/v4/bankgw/indexhtmlOTP.php?mamount=100.26&ssl_id=25090911115818LFRuUEZGgZ0sE&Q=REDIRECT&SESSIONKEY=5F6E5AEA7C0496EA63C0150C43B0207F&tran_type=success&cardname=ebl_master'}, {'name': 'VISA-City Bank', 'type': 'visa', 'logo': 'https://sandbox.sslcommerz.com/gwprocess/v4/image/gw/visa.png', 'gw': 'city_visa', 'r_flag': '1', 'redirectGatewayURL': 'https://sandbox.sslcommerz.com/gwprocess/v4/bankgw/indexhtmlOTP.php?mamount=100.26&ssl_id=25090911115818LFRuUEZGgZ0sE&Q=REDIRECT&SESSIONKEY=5F6E5AEA7C0496EA63C0150C43B0207F&tran_type=success&cardname=city_visa'}, {'name': 'MASTER-City bank', 'type': 'master', 'logo': 'https://sandbox.sslcommerz.com/gwprocess/v4/image/gw/master.png', 'gw': 'city_master', 'r_flag': '1', 'redirectGatewayURL': 'https://sandbox.sslcommerz.com/gwprocess/v4/bankgw/indexhtmlOTP.php?mamount=100.26&ssl_id=25090911115818LFRuUEZGgZ0sE&Q=REDIRECT&SESSIONKEY=5F6E5AEA7C0496EA63C0150C43B0207F&tran_type=success&cardname=city_master'}, {'name': 'TAP', 'type': 'mobilebanking', 'logo': 'https://sandbox.sslcommerz.com/gwprocess/v4/image/gw/tap.png', 'gw': 'mobilemoney', 'r_flag': '1', 'redirectGatewayURL': 'https://sandbox.sslcommerz.com/gwprocess/v4/bankgw/indexhtmlOTP.php?mamount=100.26&ssl_id=25090911115818LFRuUEZGgZ0sE&Q=REDIRECT&SESSIONKEY=5F6E5AEA7C0496EA63C0150C43B0207F&tran_type=success&cardname=mobilemoney'}, {'name': 'upay', 'type': 'mobilebanking', 'logo': 'https://sandbox.sslcommerz.com/gwprocess/v4/image/gw/upay.png', 'gw': 'upay', 'r_flag': '1', 'redirectGatewayURL': 'https://sandbox.sslcommerz.com/gwprocess/v4/bankgw/indexhtmlOTP.php?mamount=100.26&ssl_id=25090911115818LFRuUEZGgZ0sE&Q=REDIRECT&SESSIONKEY=5F6E5AEA7C0496EA63C0150C43B0207F&tran_type=success&cardname=upay'}, {'name': 'okaywallet', 'type': 'mobilebanking', 'logo': 'https://sandbox.sslcommerz.com/gwprocess/v4/image/gw/okwallet.png', 'gw': 'okaywallet', 'r_flag': '1', 'redirectGatewayURL': 'https://sandbox.sslcommerz.com/gwprocess/v4/bankgw/indexhtmlOTP.php?mamount=100.26&ssl_id=25090911115818LFRuUEZGgZ0sE&Q=REDIRECT&SESSIONKEY=5F6E5AEA7C0496EA63C0150C43B0207F&tran_type=success&cardname=okaywallet'}, {'name': 'cellfine', 'type': 'mobilebanking', 'logo': 'https://sandbox.sslcommerz.com/gwprocess/v4/image/gw/cellfin.png', 'gw': 'cellfine', 'r_flag': '1', 'redirectGatewayURL': 'https://sandbox.sslcommerz.com/gwprocess/v4/bankgw/indexhtmlOTP.php?mamount=100.26&ssl_id=25090911115818LFRuUEZGgZ0sE&Q=REDIRECT&SESSIONKEY=5F6E5AEA7C0496EA63C0150C43B0207F&tran_type=success&cardname=cellfine'}, {'name': 'mcash', 'type': 'mobilebanking', 'logo': 'https://sandbox.sslcommerz.com/gwprocess/v4/image/gw/ibblmobile.png', 'gw': 'ibbl_m', 'r_flag': '1', 'redirectGatewayURL': 'https://sandbox.sslcommerz.com/gwprocess/v4/bankgw/indexhtmlOTP.php?mamount=100.26&ssl_id=25090911115818LFRuUEZGgZ0sE&Q=REDIRECT&SESSIONKEY=5F6E5AEA7C0496EA63C0150C43B0207F&tran_type=success&cardname=ibbl_m'}, {'name': 'tapnpay', 'type': 'internetbanking', 'logo': 'https://sandbox.sslcommerz.com/gwprocess/v4/image/gw/tapnpay.png', 'gw': 'tapnpay', 'r_flag': '1', 'redirectGatewayURL': 'https://sandbox.sslcommerz.com/gwprocess/v4/bankgw/indexhtmlOTP.php?mamount=100.26&ssl_id=25090911115818LFRuUEZGgZ0sE&Q=REDIRECT&SESSIONKEY=5F6E5AEA7C0496EA63C0150C43B0207F&tran_type=success&cardname=tapnpay'}, {'name': 'eblsky', 'type': 'internetbanking', 'logo': 'https://sandbox.sslcommerz.com/gwprocess/v4/image/gw/eblsky.png', 'gw': 'eblsky', 'r_flag': '1', 'redirectGatewayURL': 'https://sandbox.sslcommer 'https://sandbox.sslcommerz.com/gwprocess/v4/bankgw/indexhtmlOTP.php?mamount=100.26&ssl_id=25090911115818LFRuUEZGgZ0sE&Q=REDIRECT&SESSIONKEY=5F6E5AEA7C0496EA63C0150C43B0207F&tran_type=success&cardname=instapay'}, {'name': 'pmoney', 'type': 'internetbanking', 'logo': 'https://sandbox.sslcommerz.com/gwprocess/v4/image/gw/pmoney.png', 'gw': 'pmoney', 'r_flag': '1', 'redirectGatewayURL': 'https://sandbox.sslcommerz.com/gwprocess/v4/bankgw/indexhtmlOTP.php?mamount=100.26&ssl_id=25090911115818LFRuUEZGgZ0sE&Q=REDIRECT&SESSIONKEY=5F6E5AEA7C0496EA63C0150C43B0207F&tran_type=success&cardname=pmoney'}, {'name': 'woori', 'type': 'internetbanking', 'logo': 'https://sandbox.sslcommerz.com/gwprocess/v4/image/gw/woori.png', 'gw': 'woori', 'r_flag': '1', 'redirectGatewayURL': 'https://sandbox.sslcommerz.com/gwprocess/v4/bankgw/indexhtmlOTP.php?mamount=100.26&ssl_id=25090911115818LFRuUEZGgZ0sE&Q=REDIRECT&SESSIONKEY=5F6E5AEA7C0496EA63C0150C43B0207F&tran_type=success&cardname=woori'}, {'name': 'modhumoti', 'type': 'internetbanking', 'logo': 'https://sandbox.sslcommerz.com/gwprocess/v4/image/gw/modhumoti.png', 'gw': 'modhumoti', 'r_flag': '1', 'redirectGatewayURL': 'https://sandbox.sslcommerz.com/gwprocess/v4/bankgw/indexhtmlOTP.php?mamount=100.26&ssl_id=25090911115818LFRuUEZGgZ0sE&Q=REDIRECT&SESSIONKEY=5F6E5AEA7C0496EA63C0150C43B0207F&tran_type=success&cardname=modhumoti'}, {'name': 'fsibl', 'type': 'internetbanking', 'logo': 'https://sandbox.sslcommerz.com/gwprocess/v4/image/gw/FsiblCloudLogo.png', 'gw': 'fsibl', 'r_flag': '1', 'redirectGatewayURL': 'https://sandbox.sslcommerz.com/gwprocess/v4/bankgw/indexhtmlOTP.php?mamount=100.26&ssl_id=25090911115818LFRuUEZGgZ0sE&Q=REDIRECT&SESSIONKEY=5F6E5AEA7C0496EA63C0150C43B0207F&tran_type=success&cardname=fsibl'}], 'is_direct_pay_enable': '0'}
[09/Sep/2025 11:11:57] "POST /api/payment/initiate/ HTTP/1.1" 200 18929
[09/Sep/2025 11:11:57] "GET /__debug__/history_sidebar/?store_id=3be834d19c974e10a9abbf8922e90497 HTTP/1.1" 200 9854
"""
