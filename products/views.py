# products, views.py: 
from products.models import Product, Category, Review, ProductImage
from products.serializers import ProductSerializer, CategorySerializer, ReviewSerializer, ProductImageSerializer
from django.db.models import Count
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend # --- 'django_filters'
from products.filters import ProductFilter
from rest_framework.filters import SearchFilter, OrderingFilter # filters
from products.paginations import DefaultPagination
from api.permissions import IsAdminOrReadOnly # custom permission
from products.permissions import IsReviewAuthorOrReadonly
from drf_yasg.utils import swagger_auto_schema
#
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from rest_framework.decorators import api_view
from django.shortcuts import get_object_or_404
from rest_framework.reverse import reverse
from rest_framework.views import APIView
from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser, IsAuthenticatedOrReadOnly
from rest_framework.permissions import DjangoModelPermissions, DjangoModelPermissionsOrAnonReadOnly  # module 23.6


@api_view(['GET','POST'])
def view_products(request):  # fbv, module 20.1 # http://127.0.0.1:8000/api/products2/product-list/
    #return HttpResponse("Okay")
    #return Response({'message':"Hello from Anup"})
    if request.method == 'GET':
        products = Product.objects.select_related('category').all()
        serializer = ProductSerializer(products, many=True, context={'request': request})  # --- context for HyperlinkedRelatedField in serializers
        return Response(serializer.data)
    if request.method == 'POST':
        # Deserializer
        serializer = ProductSerializer(data=request.data, context={'request': request}) # ---        
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

"""
# APIView
# https://www.django-rest-framework.org/api-guide/views/
class ViewProducts(APIView): # module 21.1
    # permission_classes = [AllowAny]
    def get(self, request):  # better: def get(self, request, *args, **kwargs)
        products = Product.objects.select_related('category').all()
        serializer = ProductSerializer(products, many=True, context={'request': request})  # --- context for HyperlinkedRelatedField in serializers
        return Response(serializer.data)
    def post(self, request):
        serializer = ProductSerializer(data=request.data, context={'request': request}) # ---        
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
"""

"""
# mixins & generic APIView
# https://www.django-rest-framework.org/api-guide/generic-views/#mixins
# https://www.cdrf.co/3.14/rest_framework.generics/ListCreateAPIView.html
class ProductList(ListCreateAPIView):
    queryset = Product.objects.select_related('category').all()
    serializer_class = ProductSerializer
    # def get_queryset(self): # if custom queryset needs to be sent
    #     return Product.objects.select_related('category').all()
    # def get_serializer_class(self):
    #     return ProductSerializer
    # def get_serializer_context(self):
    #     return {'request':self.request}
"""

@api_view(['GET', 'PUT', 'DELETE'])
def view_specific_product(request, id):  # module 20.2  # http://127.0.0.1:8000/api/products2/40/
    if request.method == 'GET':
        product = get_object_or_404(Product, pk=id)
        serializer = ProductSerializer(product)
        return Response(serializer.data)
    if request.method == 'PUT':
        product = get_object_or_404(Product, pk=id)
        serializer = ProductSerializer(product, data=request.data,)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    if request.method == 'DELETE':
        product = get_object_or_404(Product, pk=id)
        copy_of_product = product
        product.delete()
        serializer = ProductSerializer(copy_of_product)
        return Response(serializer.data, status=status.HTTP_204_NO_CONTENT)


@api_view()  # only allow GET requests by default
def view_categories(request):
    categories = Category.objects.annotate(product_count=Count('products')).all()        
    serializer = CategorySerializer(categories, many=True)
    return Response(serializer.data)


@api_view()
def view_specific_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    #category = get_object_or_404(Category.objects.annotate(product_count=Count('products')).all(), pk=pk)
    serializer = CategorySerializer(category)
    return Response(serializer.data)


class ProductViewSet(ModelViewSet):
    """
    API endpoint for managing products in the e-commerce store
     - Allows authenticated admin to create, update, and delete products
     - Allows users to browse and filter product
     - Support searching by name, description, and category
     - Support ordering by price and updated_at
    """
    
    #queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter  # uses 'django_filters'
    pagination_class = DefaultPagination
    search_fields = ['name', 'description'] # 
    ordering_fields = ['price', 'updated_at']
    permission_classes = [IsAdminOrReadOnly]  # custom permission
    # permission_classes = [DjangoModelPermissionsOrAnonReadOnly]  # for edit, can give group permission(can crud a specific model) to a user.

    @swagger_auto_schema(
        operation_summary='Retrive a list of products'
    )
    def list(self, request, *args, **kwargs):
        """Retrive all the products"""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create a product by admin",
        operation_description="This allow an admin to create a product",
        request_body=ProductSerializer,
        responses={
            201: ProductSerializer,
            400: "Bad Request"
        }
    )
    def create(self, request, *args, **kwargs):
        #Only authenticated admin can create product
        return super().create(request, *args, **kwargs)
    queryset = Product.objects.all() 
    # following is not needed, as ProductFilter handles the filter.
    # def get_queryset(self):        
    #     category_id = self.request.query_params.get('category_id')
    #     if category_id is not None:
    #         queryset = Product.objects.filter(category_id=category_id)  # eg. http://127.0.0.1:8000/api/products/?category_id=1
    #     else:
    #         queryset = Product.objects.all()   
    #     return queryset


class ProductImageViewSet(ModelViewSet):
    serializer_class = ProductImageSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        return ProductImage.objects.filter(product_id=self.kwargs.get('product_pk'))

    def perform_create(self, serializer):
        serializer.save(product_id=self.kwargs.get('product_pk'))


class CategoryViewSet(ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]
    queryset = Category.objects.annotate(product_count=Count('products')).all()
    serializer_class = CategorySerializer


class ReviewViewSet(ModelViewSet):
    serializer_class = ReviewSerializer
    #permission_classes = [IsAuthenticated]  # ---
    permission_classes = [IsReviewAuthorOrReadonly]

    def get_queryset(self):
        # When drf-yasg is building your OpenAPI schema it instantiates every ViewSet without any URL kwargs,
        # during schema generation, swagger_fake_view == True and there are no kwargs
        if getattr(self, 'swagger_fake_view', False):
            return Review.objects.none()
        return Review.objects.filter(product_id=self.kwargs['product_pk'])

    def get_serializer_context(self):
        if getattr(self, 'swagger_fake_view', False):
            # you can either return an empty context or delegate to the base impl
            return super().get_serializer_context()
        #return {'product_id': self.kwargs['product_pk']}        
        context = super().get_serializer_context()  # Includes request(& user) by default
        context['product_id'] = self.kwargs['product_pk']
        return context
        """
        or,
        return {
            'product_id': self.kwargs['product_pk'],
            'request': self.request,  # <-- add this
        }
        """
    """
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    def perform_update(self, serializer):
        serializer.save(user=self.request.user)
    """
        
    # alternatively override perform_create, remove get_serializer_context, and create method from the serializer. 
    # def perform_create(self, serializer):
    #     serializer.save(
    #         user=self.request.user,  # Set current user
    #         product_id=self.kwargs['product_pk']  # Set product from URL
    #     ) 
    


"""
class ReviewViewSet(ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [IsReviewAuthorOrReadonly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        return Review.objects.filter(product_id=self.kwargs.get('product_pk'))

    def get_serializer_context(self):
        return {'product_id': self.kwargs.get('product_pk')}
"""

"""
review urls:

http://127.0.0.1:8000/api/products/1/reviews/

http://127.0.0.1:8000/api/products/1/reviews/1/

"""