# api, auth_views.py
from datetime import timezone
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.response import Response
from rest_framework import status

class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            
            if response.status_code == 200:
                # Get the user from the validated data
                user = self.user  # This is set by the parent class after validation
                
                # Update last_login
                user.last_login = timezone.now()
                user.save(update_fields=['last_login'])
            
            return response
        except Exception as e:
            # If authentication fails, just return the error response
            return super().post(request, *args, **kwargs)
        

# to update last_login when using jwt tokens
