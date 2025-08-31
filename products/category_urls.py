from django.urls import path
from products import views

app_name = 'products'

urlpatterns = [
    path('', views.view_categories, name='category-list'),
    path('<int:pk>/', views.view_specific_category, name='view-specific-category')
]
