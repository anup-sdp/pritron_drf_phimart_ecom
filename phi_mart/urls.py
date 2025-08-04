"""
URL configuration for phi_mart project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from api.views import api_root_view
from debug_toolbar.toolbar import debug_toolbar_urls
from django.conf.urls.static import static
from django.conf import settings
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

schema_view = get_schema_view(  # for drf-yasg package
    openapi.Info(
        title="PhiMart - E-commerce API",
        default_version='v1',
        description="API Documentation for Phimart E-commerce Project",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@phimart.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
	path("", api_root_view),
	path('api-auth/', include('rest_framework.urls')), # For login/logout in DRF UI
	path('api/', include('api.urls')), # , name='api-root'  # recommended format use: api/v1/ -----
	path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
	path('swagger/', schema_view.with_ui('swagger',cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc',cache_timeout=0), name='schema-redoc'),
] + debug_toolbar_urls()

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# for apis: 1) models, 2) serializers, 3) viewset, 4) router