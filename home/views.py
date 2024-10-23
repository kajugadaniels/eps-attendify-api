from home.serializers import *
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from rest_framework.generics import ListAPIView
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

class AssignPermissionView(APIView):
    """
    View to assign multiple permissions to a user. Handles cases where the user already has the permission and ensures only authorized users can assign permissions.
    """
    # Restrict this API to only those who can manage user permissions
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            # Check if the user has the permission to assign permissions
            if not request.user.has_perm('auth.change_user'):
                raise PermissionDenied({'message': "You do not have permission to assign permissions."})

        user_id = request.data.get('user_id')
        permission_codenames = request.data.get('permission_codename', [])
        response_data = []

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'message': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        for codename in permission_codenames:
            try:
                permission = Permission.objects.get(codename=codename)
                if user.user_permissions.filter(id=permission.id).exists():
                    response_data.append({'codename': codename, 'status': f'User already has the "{codename}" permission.'})
                else:
                    user.user_permissions.add(permission)
                    response_data.append({'codename': codename, 'status': 'Permission assigned successfully.'})
            except Permission.DoesNotExist:
                response_data.append({'codename': codename, 'status': 'Permission not found.'})

        if any(item['status'].startswith('User already has') for item in response_data):
            return Response({'results': response_data}, status=status.HTTP_409_CONFLICT)
        return Response({'results': response_data}, status=status.HTTP_200_OK)

class RemovePermissionView(APIView):
    """
    View to remove permissions from a user.
    """
    permission_classes = [permissions.IsAdminUser]  # Only admins can access this

    def post(self, request, *args, **kwargs):
        # Superusers bypass all permissions checks
        if not request.user.is_superuser:
            # Verify the user has permission to change user permissions
            if not request.user.has_perm('auth.change_user'):
                raise PermissionDenied({'message': "You do not have permission to remove permissions."})

        user_id = request.data.get('user_id')
        permissions_codenames = request.data.get('permission_codename', [])
        results = []

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'message': "User not found."}, status=status.HTTP_404_NOT_FOUND)

        for codename in permissions_codenames:
            try:
                permission = Permission.objects.get(codename=codename)
                if user.user_permissions.filter(id=permission.id).exists():
                    user.user_permissions.remove(permission)
                    results.append({"codename": codename, "status": "Permission removed successfully."})
                else:
                    results.append({"codename": codename, "status": "User does not have the specified permission."})
            except Permission.DoesNotExist:
                results.append({"codename": codename, "status": "Permission not found."})

        return Response({"results": results}, status=status.HTTP_200_OK)

class UserPermissionsView(APIView):
    """
    View to list all permissions of a specific user.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, user_id, *args, **kwargs):
        # Superusers can access without restrictions
        if not request.user.is_superuser:
            # Check if the user has permission to view user permissions
            if not request.user.has_perm('auth.view_permission'):
                raise PermissionDenied({'message': "You do not have permission to perform this action."})

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'message': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            # Retrieve all user permissions, including group permissions
            user_permissions = user.user_permissions.all() | Permission.objects.filter(group__user=user)
            permissions_data = [{
                'id': perm.id,
                'name': perm.name,
                'codename': perm.codename,
                'content_type': perm.content_type.model
            } for perm in user_permissions.distinct()]

            return Response({
                'message': 'Permissions retrieved successfully.',
                'permissions': permissions_data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'message': 'Failed to retrieve permissions.',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserListView(APIView):
    """
    API view to list all users with their roles.
    Only superusers and users with the 'Admin' role can view users.
    """
    permission_classes = [IsAuthenticated]  # Allow access to authenticated users

    def get(self, request):
        try:
            # Check if the user is a superuser or has the role of 'Admin'
            if request.user.is_superuser:
                users = User.objects.all().order_by('-id')
            else:
                # If the user is not authorized, return a forbidden response
                return Response({"error": "You do not have permission to view this resource."},
                                status=status.HTTP_403_FORBIDDEN)

            # Serialize user data with roles
            serializer = UserSerializer(users, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserDetailView(APIView):
    """
    API view to retrieve, update, or delete a user's details by their ID.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    def get(self, request, user_id):
        user = self.get_object(user_id)
        if user is None:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, user_id):
        user = self.get_object(user_id)
        if user is None:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        # Permission check: Only superusers or the user themselves can update
        if not request.user.is_superuser and request.user.id != user.id:
            return Response({"error": "You do not have permission to edit this user."}, status=status.HTTP_403_FORBIDDEN)

        serializer = UserSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "User updated successfully", "user": serializer.data}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, user_id):
        user = self.get_object(user_id)
        if user is None:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        # Permission check: Only superusers or users with specific permission can delete
        if not request.user.is_superuser:
            return Response({"error": "You do not have permission to delete this user."}, status=status.HTTP_403_FORBIDDEN)

        # Deleting the user
        user.delete()
        return Response({"message": "User deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

class DepartmentListCreateView(APIView):
    """
    API view to list all departments with their roles or create a new department.
    Only superuser and departments with the 'Admin' role can view or add departments.
    """
    permission_classes = [IsAuthenticated]  # Allow access to authenticated departments

    def get(self, request):
        try:
            # Check if the department is a superuser or has the role of 'Admin'
            if request.user.is_superuser or request.user.role == 'Admin':
                departments = Department.objects.all().order_by('-id')
            else:
                # If the department is not authorized, return a forbidden response
                return Response({"error": "You do not have permission to view this resource."},
                                status=status.HTTP_403_FORBIDDEN)

            # Serialize department data with roles
            serializer = DepartmentSerializer(departments, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        try:
            # Only superuser and departments with the 'Admin' role can create new departments
            if not request.user.is_superuser and request.user.role != 'Admin':
                return Response({"error": "You do not have permission to add a new department."},
                                status=status.HTTP_403_FORBIDDEN)

            # Use the DepartmentSerializer to validate and create a new department
            serializer = DepartmentSerializer(data=request.data)
            if serializer.is_valid():
                department = serializer.save()
                return Response({
                    "message": "Department created successfully",
                    "department": DepartmentSerializer(department).data
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    "message": "Department creation failed",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DepartmentRetrieveUpdateDestroyView(APIView):
    """
    API view to retrieve, update, or delete a department's details by their ID.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, department_id):
        try:
            return Department.objects.get(id=department_id)
        except Department.DoesNotExist:
            return None

    def get(self, request, department_id):
        department = self.get_object(department_id)
        if department is None:
            return Response({"error": "Department not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = DepartmentSerializer(department)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, department_id):
        department = self.get_object(department_id)
        if department is None:
            return Response({"error": "Department not found"}, status=status.HTTP_404_NOT_FOUND)

        # Permission check: Only superusers or the user themselves can update
        if not request.user.is_superuser:
            return Response({"error": "You do not have permission to update this department."}, status=status.HTTP_403_FORBIDDEN)

        serializer = DepartmentSerializer(department, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Department updated successfully", "user": serializer.data}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, department_id):
        department = self.get_object(department_id)
        if department is None:
            return Response({"error": "Department not found"}, status=status.HTTP_404_NOT_FOUND)

        # Permission check: Only superusers or users with specific permission can delete
        if not request.user.is_superuser:
            return Response({"error": "You do not have permission to delete this user."}, status=status.HTTP_403_FORBIDDEN)

        # Deleting the department
        department.delete()
        return Response({"message": "Department deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

class EmployeeListCreateView(APIView):
    """
    API view to list all employees with their roles or create a new empployee.
    Only superuser and employees with the 'Admin' role can view or add employees.
    """
    permission_classes = [IsAuthenticated]  # Allow access to authenticated employees

    def get(self, request):
        try:
            # Check if the employee is a superuser or has the role of 'Admin'
            if request.user.is_superuser or request.user.role == 'Admin':
                employees = Employee.objects.all().order_by('-id')
            else:
                # If the employee is not authorized, return a forbidden response
                return Response({"error": "You do not have permission to view this resource."},
                                status=status.HTTP_403_FORBIDDEN)

            # Serialize employee data with roles
            serializer = EmployeeSerializer(employees, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        try:
            # Only superuser and employees with the 'Admin' role can create new employees
            if not request.user.is_superuser and request.user.role != 'Admin':
                return Response({"error": "You do not have permission to add a new employee."},
                                status=status.HTTP_403_FORBIDDEN)

            # Use the EmployeeSerializer to validate and create a new employee
            serializer = EmployeeSerializer(data=request.data)
            if serializer.is_valid():
                employee = serializer.save()
                return Response({
                    "message": "Employee created successfully",
                    "employee": EmployeeSerializer(employee).data
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    "message": "Employee creation failed",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class EmployeeRetrieveUpdateDestroyView(APIView):
    """
    API view to retrieve, update, or delete a employee's details by their ID.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, employee_id):
        try:
            return Employee.objects.get(id=employee_id)
        except Employee.DoesNotExist:
            return None

    def get(self, request, employee_id):
        employee = self.get_object(employee_id)
        if employee is None:
            return Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = EmployeeSerializer(employee)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, employee_id):
        employee = self.get_object(employee_id)
        if employee is None:
            return Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)

        # Permission check: Only superusers or the user themselves can update
        if not request.user.is_superuser:
            return Response({"error": "You do not have permission to update this employee."}, status=status.HTTP_403_FORBIDDEN)

        serializer = EmployeeSerializer(employee, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Employee updated successfully", "user": serializer.data}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, employee_id):
        employee = self.get_object(employee_id)
        if employee is None:
            return Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)

        # Permission check: Only superusers or users with specific permission can delete
        if not request.user.is_superuser:
            return Response({"error": "You do not have permission to delete this user."}, status=status.HTTP_403_FORBIDDEN)

        # Deleting the employee
        employee.delete()
        return Response({"message": "Employee deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

class FieldListCreateView(APIView):
    """
    API view to list all fields with their roles or create a new field.
    Only superuser and fields with the 'Admin' role can view or add fields.
    """
    permission_classes = [IsAuthenticated]  # Allow access to authenticated fields

    def get(self, request):
        try:
            # Check if the field is a superuser or has the role of 'Admin'
            if request.user.is_superuser or request.user.role == 'Admin':
                fields = Field.objects.all().order_by('-id')
            else:
                # If the field is not authorized, return a forbidden response
                return Response({"error": "You do not have permission to view this resource."},
                                status=status.HTTP_403_FORBIDDEN)

            # Serialize field data with roles
            serializer = FieldSerializer(fields, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        try:
            # Only superuser and fields with the 'Admin' role can create new fields
            if not request.user.is_superuser and request.user.role != 'Admin':
                return Response({"error": "You do not have permission to add a new field."},
                                status=status.HTTP_403_FORBIDDEN)

            # Use the FieldSerializer to validate and create a new field
            serializer = FieldSerializer(data=request.data)
            if serializer.is_valid():
                field = serializer.save()
                return Response({
                    "message": "Field created successfully",
                    "field": FieldSerializer(field).data
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    "message": "Field creation failed",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class FieldRetrieveUpdateDestroyView(APIView):
    """
    API view to retrieve, update, or delete a field's details by their ID.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, field_id):
        try:
            return Field.objects.get(id=field_id)
        except Field.DoesNotExist:
            return None

    def get(self, request, field_id):
        field = self.get_object(field_id)
        if field is None:
            return Response({"error": "Field not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = FieldSerializer(field)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, field_id):
        field = self.get_object(field_id)
        if field is None:
            return Response({"error": "Field not found"}, status=status.HTTP_404_NOT_FOUND)

        # Permission check: Only superusers or the user themselves can update
        if not request.user.is_superuser:
            return Response({"error": "You do not have permission to update this field."}, status=status.HTTP_403_FORBIDDEN)

        serializer = FieldSerializer(field, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Field updated successfully", "user": serializer.data}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, field_id):
        field = self.get_object(field_id)
        if field is None:
            return Response({"error": "Field not found"}, status=status.HTTP_404_NOT_FOUND)

        # Permission check: Only superusers or users with specific permission can delete
        if not request.user.is_superuser:
            return Response({"error": "You do not have permission to delete this field."}, status=status.HTTP_403_FORBIDDEN)

        # Deleting the user
        field.delete()
        return Response({"message": "Field deleted successfully"}, status=status.HTTP_204_NO_CONTENT)