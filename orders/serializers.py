# orders, serializers.py:
from rest_framework import serializers
from orders.models import Cart, CartItem, Order, OrderItem
from products.models import Product
from products.serializers import ProductSerializer
from orders.services import OrderService


class EmptySerializer(serializers.Serializer):
    pass


class SimpleProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'price']


class AddCartItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField()

    class Meta:
        model = CartItem
        fields = ['id', 'product_id', 'quantity']

    def save(self, **kwargs):
        cart_id = self.context['cart_id']
        product_id = self.validated_data['product_id']
        quantity = self.validated_data['quantity']

        try:
            cart_item = CartItem.objects.get(cart_id=cart_id, product_id=product_id)                
            cart_item.quantity += quantity
            #self.instance = cart_item.save() # ---- .save() returns None
            cart_item.save()
            self.instance = cart_item
        except CartItem.DoesNotExist:
            self.instance = CartItem.objects.create(
                cart_id=cart_id, **self.validated_data)

        return self.instance

    def validate_product_id(self, value):
        if not Product.objects.filter(pk=value).exists():
            raise serializers.ValidationError(f"Product with id {value} does not exists")                
        return value


class UpdateCartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ['quantity']


class CartItemSerializer(serializers.ModelSerializer):
    product = SimpleProductSerializer()
    total_price = serializers.SerializerMethodField(
        method_name='get_total_price')

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'quantity', 'product', 'total_price']

    def get_total_price(self, cart_item: CartItem):
        return cart_item.quantity * cart_item.product.price


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True) # read_only, wont ask for items while creating Cart
    total_price = serializers.SerializerMethodField(method_name='get_total_price')       

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'total_price']
        read_only_fields = ['user']

    def get_total_price(self, cart: Cart):  # type mention
        return sum([item.product.price * item.quantity for item in cart.items.all()])            


class CreateOrderSerializer(serializers.Serializer): # not ModelSerializer
    cart_id = serializers.UUIDField()

    def validate_cart_id(self, cart_id):
        if not Cart.objects.filter(pk=cart_id).exists():
            raise serializers.ValidationError('No cart found with this id')

        if not CartItem.objects.filter(cart_id=cart_id).exists():
            raise serializers.ValidationError('Cart is empty')

        return cart_id

    def create(self, validated_data):
        user_id = self.context['user_id']
        cart_id = validated_data['cart_id']

        try:
            order = OrderService.create_order(user_id=user_id, cart_id=cart_id) # --- separation
            return order
        except ValueError as e:
            raise serializers.ValidationError(str(e))

    def to_representation(self, instance):  # 'cause "return order" above giving error --- search details ---
        # “instance” is the Order returned by create()
        return OrderSerializer(instance).data
"""
^
the to_representation method is used in the CreateOrderSerializer to customize how the newly created 
Order instance is serialized into a response format after the create method is executed

CreateOrderSerializer is a plain serializers.Serializer (not ModelSerializer), so it has no built-in knowledge of how to convert an Order model instance to JSON.
When create() returns the raw Order instance, DRF tries to call .data on the serializer, but without to_representation, 
it would only include fields defined in CreateOrderSerializer (just cart_id), not the actual order data.

When a non-ModelSerializer returns a model instance from create(), you must implement to_representation to tell DRF 
how to convert that instance to JSON. Otherwise, the API response will lack meaningful data about the created object.
"""

class OrderItemSerializer(serializers.ModelSerializer):
    product = SimpleProductSerializer()

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'price', 'quantity', 'total_price']


class UpdateOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['status']
        
    """
    # removed after adding @action in views, module 24.8
    def update(self, instance, validated_data):
        user = self.context['user']
        new_status = validated_data['status']

        if new_status == Order.CANCELED:
            return OrderService.cancel_order(order=instance, user=user)

        # Admin kina
        if not user.is_staff:
            raise serializers.ValidationError(
                {'detail':  'You are not allowed to update this order'}
            )

        return super().update(instance, validated_data)
    """	


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = ['id', 'user', 'status', 'total_price', 'created_at', 'items']
