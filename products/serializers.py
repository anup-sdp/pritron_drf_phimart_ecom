from rest_framework import serializers
from decimal import Decimal
from products.models import Category, Product, Review, ProductImage
from django.contrib.auth import get_user_model


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'product_count']

    product_count = serializers.IntegerField(read_only=True, help_text="Return the number product in this category") # help_text for swagger show

class ProductImageSerializer(serializers.ModelSerializer):
    image= serializers.ImageField()
    class Meta:
        model = ProductImage
        fields = ['id', 'image']
    def validate_image(self, value):
        # Limit file size to 1MB
        if value.size > 1 * 1024 * 1024:
            raise serializers.ValidationError("Image size cannot exceed 1MB.")
        # Check file type
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
        if not any(value.name.lower().endswith(ext) for ext in valid_extensions):
            raise serializers.ValidationError("Unsupported file type.")
        return value    

"""
class ProductSerializer(serializers.Serializer):  # module 20.4
    id = serializers.IntegerField()
    name = serializers.CharField()
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, source='price')
    price_with_tax = serializers.SerializerMethodField(method_name='calculate_tax')
    # category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all() )
    # category = serializers.StringRelatedField()
    # category = CategorySerializer()
    
    category = serializers.HyperlinkedRelatedField(queryset=Category.objects.all(), view_name='view-specific-category')
    
    def calculate_tax(self, product):
        return round(product.price * Decimal(1.1), 2)
"""

""""""
class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'price','stock', 'category', 'price_with_tax', 'images']  # other, '__all__'

    price_with_tax = serializers.SerializerMethodField(method_name='calculate_tax')  
    #category = serializers.HyperlinkedRelatedField(queryset=Category.objects.all(), view_name='products:view-specific-category')
	# ^ problem with creation new elem in post method. 
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    def calculate_tax(self, product):
        return round(product.price * Decimal(1.1), 2)
	# serializer validation
    def validate_price(self, price):
        if price < 0:
            raise serializers.ValidationError("Price can't be negative")
        return price



class SimpleUserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField(method_name='get_current_user_name')
    
    class Meta:
        model = get_user_model()
        fields = ['id', 'name']

    def get_current_user_name(self, obj):
        return obj.get_full_name()


class ReviewSerializer(serializers.ModelSerializer):
    # user = SimpleUserSerializer()
    user = serializers.SerializerMethodField(method_name='get_user')

    class Meta:
        model = Review
        fields = ['id', 'user', 'product', 'ratings', 'comment']
        read_only_fields = ['user', 'product']  # DRF's Browsable API automatically hides read-only fields

    def get_user(self, obj):
        return SimpleUserSerializer(obj.user).data

    def create(self, validated_data):
        # product_id = self.context['product_id']        
        # return Review.objects.create(product_id=product_id, **validated_data)
        # Get current user from request
        user = self.context['request'].user
        product_id = self.context['product_id']
        # Explicitly assign user and product
        return Review.objects.create(user=user, product_id=product_id, **validated_data)
