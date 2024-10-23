from account.serializers import *
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from rest_framework.generics import GenericAPIView
from django.core.exceptions import PermissionDenied
from rest_framework import generics, permissions, status
from rest_framework.permissions import IsAuthenticated, AllowAny

class PermissionListView(generics.ListAPIView):
    """
    View to list all permissions. Accessible only to users with appropriate permissions or superusers.
    """
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAuthenticated] # Change to ensure only authenticated users can access

    def get_queryset(self):
        # Allow superusers unrestricted access
        if self.request.user.is_superuser:
            return super().get_queryset()

        # Check if the user has the 'view_permission' permission
        if not self.request.user.has_perm('auth.view_permission'):
            raise PermissionDenied({'message': "You do not have permission to view permissions."})

        return super().get_queryset()

class LoginView(GenericAPIView):  # Change to GenericAPIView
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer  # Ensure serializer is set

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)  # Use get_serializer method
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        user = authenticate(username=email, password=password)

        if user:
            # Delete old token and generate a new one
            Token.objects.filter(user=user).delete()
            token, created = Token.objects.get_or_create(user=user)

            return Response({
                'token': token.key,
                'user': UserSerializer(user).data,  # Use your user serializer if needed
                'message': 'Login successful.'
            }, status=status.HTTP_200_OK)
        return Response({'error': 'Invalid email or password.'}, status=status.HTTP_400_BAD_REQUEST)