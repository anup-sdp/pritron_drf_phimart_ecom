from django.contrib import admin
from products.models import Product, Category, Review, ProductImage


admin.site.register(Product)
admin.site.register(ProductImage)
admin.site.register(Category)
admin.site.register(Review)
