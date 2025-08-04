# users, serializers.py:
# https://djoser.readthedocs.io/en/latest/settings.html#serializers
from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer, UserSerializer as BaseUserSerializer


class UserCreateSerializer(BaseUserCreateSerializer):
    class Meta(BaseUserCreateSerializer.Meta):
        fields = ['id', 'email', 'password', 'first_name', 'last_name', 'address', 'phone_number']


#class UserSerializer(BaseUserSerializer):
class UserSerializer(BaseUserSerializer):
    class Meta(BaseUserSerializer.Meta):
        ref_name = 'CustomUser' # used to fix below error, or change this class name to CustomUserSerializer here and in settings DJOSER, 'current_user' reference
        fields = ['id', 'email', 'first_name', 'last_name', 'address', 'phone_number']

"""
# if visit, http://127.0.0.1:8000/swagger/ , getting error:
raise SwaggerGenerationError(
drf_yasg.errors.SwaggerGenerationError: Schema for <class 'djoser.serializers.UserSerializer'> would override 
distinct serializer <class 'users.serializers.UserSerializer'> because they implicitly share the same ref_name; 
explicitly set the ref_name attribute on both serializers' Meta classes
fix: use, ref_name = 'CustomUser'
"""