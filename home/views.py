from home.serializers import *
from django.db import transaction
from django.db.models import Count, Q
from rest_framework.views import APIView
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.core.exceptions import PermissionDenied
from rest_framework import generics, permissions, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes

class PermissionListView(generics.ListAPIView):
    """
    View to list all permissions. Accessible only to users with appropriate permissions or superusers.
    """
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAuthenticated]

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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getUsers(request):
    """
    Function-based view to list all users with their roles.
    Only superusers can view all users.
    """
    try:
        if request.user.is_superuser:
            users = User.objects.all().order_by('-id')
        else:
            return Response(
                {"error": "You do not have permission to view this resource."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getUserDetail(request, user_id):
    """
    Function-based view to retrieve a user's details by ID.
    """
    try:
        user = User.objects.filter(id=user_id).first()
        if not user:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def updateUser(request, user_id):
    """
    Function-based view to update a user's details.
    Only superusers or the user themselves can update their details.
    """
    try:
        user = User.objects.filter(id=user_id).first()
        if not user:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check permission: only superuser or the user themselves may update
        if not request.user.is_superuser and request.user.id != user.id:
            return Response(
                {"error": "You do not have permission to edit this user."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = UserSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "User updated successfully", "user": serializer.data},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def deleteUser(request, user_id):
    """
    Function-based view to delete a user.
    Only superusers are allowed to delete a user.
    """
    try:
        user = User.objects.filter(id=user_id).first()
        if not user:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Only superusers can delete users
        if not request.user.is_superuser:
            return Response(
                {"error": "You do not have permission to delete this user."},
                status=status.HTTP_403_FORBIDDEN
            )

        user.delete()
        return Response(
            {"message": "User deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

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

class AssignmentListCreateView(APIView):
    """
    API view to list all assignments or create a new assignment group.
    Shows detailed information including all employees, field, and department details.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Check if the user is authorized
            if not (request.user.is_superuser or request.user.role == 'Admin'):
                return Response(
                    {"error": "You do not have permission to view assignments."},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Get query parameters for filtering
            field_id = request.query_params.get('field')
            department_id = request.query_params.get('department')
            is_active = request.query_params.get('is_active')
            
            # Start with all assignment groups
            assignments = AssignmentGroup.objects.all()
            
            # Apply filters if provided
            if field_id:
                assignments = assignments.filter(field_id=field_id)
            if department_id:
                assignments = assignments.filter(department_id=department_id)
            if is_active is not None:
                is_active = is_active.lower() == 'true'
                assignments = assignments.filter(is_active=is_active)

            # Annotate with employee counts
            assignments = assignments.annotate(
                total_employees=Count('employee_assignments'),
                active_employees=Count(
                    'employee_assignments',
                    filter=Q(employee_assignments__status='active')
                )
            ).order_by('-id')

            # Serialize the data with the detailed serializer
            serializer = AssignmentGroupDetailSerializer(assignments, many=True)
            
            return Response({
                "count": assignments.count(),
                "results": serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request):
        try:
            # Check if user has permission to create assignments
            if not (request.user.is_superuser or request.user.role == 'Admin'):
                return Response(
                    {"error": "You do not have permission to create assignments."},
                    status=status.HTTP_403_FORBIDDEN
                )

            # First, create the assignment group
            group_serializer = AssignmentGroupSerializer(data=request.data)
            if not group_serializer.is_valid():
                return Response({
                    "message": "Assignment group creation failed",
                    "errors": group_serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            # Save the assignment group
            assignment_group = group_serializer.save()

            # If employees were provided, assign them to the group
            employees = request.data.get('employees', [])
            successful_assignments = []
            failed_assignments = []

            for employee_id in employees:
                try:
                    assignment = EmployeeAssignment.objects.create(
                        assignment_group=assignment_group,
                        employee_id=employee_id
                    )
                    successful_assignments.append(employee_id)
                except Exception as e:
                    failed_assignments.append({
                        "employee_id": employee_id,
                        "error": str(e)
                    })

            # Get the updated assignment group with all its details
            updated_serializer = AssignmentGroupDetailSerializer(assignment_group)

            response_data = {
                "message": "Assignment group created successfully",
                "assignment_group": updated_serializer.data,
                "assignments_summary": {
                    "successful_assignments": successful_assignments,
                    "failed_assignments": failed_assignments
                }
            }

            return Response(
                response_data,
                status=status.HTTP_201_CREATED if not failed_assignments else status.HTTP_207_MULTI_STATUS
            )

        except Exception as e:
            # If the group was created but employee assignments failed, delete the group
            if 'assignment_group' in locals():
                assignment_group.delete()
            
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AssignmentRetrieveUpdateDestroyView(APIView):
    """
    API view to retrieve, update, or delete an assignment group by its ID.
    Includes detailed information about all employees in the assignment.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, assignment_id):
        try:
            return AssignmentGroup.objects.get(id=assignment_id)
        except AssignmentGroup.DoesNotExist:
            return None

    def get(self, request, assignment_id):
        """Retrieve detailed information about a specific assignment"""
        try:
            # Check permissions
            if not (request.user.is_superuser or request.user.role == 'Admin'):
                return Response(
                    {"error": "You do not have permission to view this assignment."},
                    status=status.HTTP_403_FORBIDDEN
                )

            assignment = self.get_object(assignment_id)
            if assignment is None:
                return Response(
                    {"error": "Assignment not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            serializer = AssignmentGroupDetailSerializer(assignment)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @transaction.atomic
    def put(self, request, assignment_id):
        """Update an existing assignment group and its employee assignments"""
        try:
            # Check permissions
            if not (request.user.is_superuser or request.user.role == 'Admin'):
                return Response(
                    {"error": "You do not have permission to update this assignment."},
                    status=status.HTTP_403_FORBIDDEN
                )

            assignment = self.get_object(assignment_id)
            if assignment is None:
                return Response(
                    {"error": "Assignment not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Create a transaction savepoint
            with transaction.atomic():
                # Update basic assignment group information
                group_serializer = AssignmentGroupSerializer(
                    assignment,
                    data=request.data,
                    partial=True
                )
                if not group_serializer.is_valid():
                    return Response({
                        "message": "Assignment update failed",
                        "errors": group_serializer.errors
                    }, status=status.HTTP_400_BAD_REQUEST)

                assignment = group_serializer.save()

                # Handle employee updates if provided
                if 'employees' in request.data:
                    new_employee_ids = set(request.data['employees'])
                    current_employee_ids = set(
                        assignment.employee_assignments.values_list('employee_id', flat=True)
                    )

                    # Remove employees not in the new list
                    employees_to_remove = current_employee_ids - new_employee_ids
                    if employees_to_remove:
                        EmployeeAssignment.objects.filter(
                            assignment_group=assignment,
                            employee_id__in=employees_to_remove
                        ).delete()

                    # Add new employees
                    employees_to_add = new_employee_ids - current_employee_ids
                    for employee_id in employees_to_add:
                        try:
                            EmployeeAssignment.objects.create(
                                assignment_group=assignment,
                                employee_id=employee_id
                            )
                        except Exception as e:
                            # Log the error but continue processing
                            print(f"Error adding employee {employee_id}: {str(e)}")

                # Get updated assignment data
                updated_serializer = AssignmentGroupDetailSerializer(assignment)
                return Response({
                    "message": "Assignment updated successfully",
                    "assignment": updated_serializer.data
                }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request, assignment_id):
        """Delete an assignment group and all its employee assignments"""
        try:
            # Check permissions
            if not (request.user.is_superuser or request.user.role == 'Admin'):
                return Response(
                    {"error": "You do not have permission to delete this assignment."},
                    status=status.HTTP_403_FORBIDDEN
                )

            assignment = self.get_object(assignment_id)
            if assignment is None:
                return Response(
                    {"error": "Assignment not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Store assignment details for response
            assignment_details = AssignmentGroupDetailSerializer(assignment).data

            # Delete the assignment (this will cascade delete all employee assignments)
            assignment.delete()

            return Response({
                "message": "Assignment deleted successfully",
                "deleted_assignment": assignment_details
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class EndAssignmentView(APIView):
    """
    API view to end an assignment group and all its employee assignments.
    Sets the same end date for both the group and all employee assignments.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, assignment_id):
        try:
            return AssignmentGroup.objects.get(id=assignment_id)
        except AssignmentGroup.DoesNotExist:
            return None

    @transaction.atomic
    def post(self, request, assignment_id):
        """
        End an assignment group and all its employee assignments
        
        Expected payload:
        {
            "end_date": "YYYY-MM-DD",  # Optional, defaults to current date
            "reason": "String",        # Optional, reason for ending the assignment
        }
        """
        try:
            # Check permissions
            if not (request.user.is_superuser or request.user.role == 'Admin'):
                return Response(
                    {"error": "You do not have permission to end this assignment."},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Get the assignment group
            assignment = self.get_object(assignment_id)
            if assignment is None:
                return Response(
                    {"error": "Assignment not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Check if assignment is already ended
            if not assignment.is_active:
                return Response(
                    {"error": "This assignment has already been ended."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get end date from request or use current date
            end_date = request.data.get('end_date')
            if end_date:
                try:
                    end_date = timezone.datetime.strptime(end_date, "%Y-%m-%d").date()
                except ValueError:
                    return Response(
                        {"error": "Invalid date format. Use YYYY-MM-DD"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                end_date = timezone.now().date()

            # Validate end date
            if end_date < assignment.created_date:
                return Response(
                    {"error": "End date cannot be before the assignment start date."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Start atomic transaction
            with transaction.atomic():
                # Update assignment group
                assignment.end_date = end_date
                assignment.is_active = False
                
                # Add reason to notes if provided
                if 'reason' in request.data:
                    current_notes = assignment.notes or ""
                    timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
                    new_note = f"\n[{timestamp}] Assignment ended - Reason: {request.data['reason']}"
                    assignment.notes = current_notes + new_note
                
                try:
                    assignment.clean()  # Run model validation
                    assignment.save()
                except ValidationError as e:
                    return Response(
                        {"error": str(e)},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Update all active employee assignments
                active_assignments = EmployeeAssignment.objects.filter(
                    assignment_group=assignment,
                    status='active'
                )

                # Prepare bulk update data
                for emp_assignment in active_assignments:
                    emp_assignment.end_date = end_date
                    emp_assignment.status = 'completed'
                    try:
                        emp_assignment.clean()  # Run model validation
                    except ValidationError as e:
                        return Response(
                            {"error": f"Error updating employee {emp_assignment.employee.name}: {str(e)}"},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                # Bulk update employee assignments
                if active_assignments:
                    EmployeeAssignment.objects.bulk_update(
                        active_assignments,
                        ['end_date', 'status']
                    )

                # Get updated assignment data
                updated_serializer = AssignmentGroupDetailSerializer(assignment)

                # Prepare response summary
                response_data = {
                    "message": "Assignment ended successfully",
                    "end_date": end_date.strftime("%Y-%m-%d"),
                    "employees_updated": active_assignments.count(),
                    "assignment": updated_serializer.data
                }

                if 'reason' in request.data:
                    response_data["reason"] = request.data['reason']

                return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get(self, request, assignment_id):
        """
        Get information about whether an assignment can be ended
        and any potential issues that need to be resolved
        """
        try:
            # Check permissions
            if not (request.user.is_superuser or request.user.role == 'Admin'):
                return Response(
                    {"error": "You do not have permission to view this information."},
                    status=status.HTTP_403_FORBIDDEN
                )

            assignment = self.get_object(assignment_id)
            if assignment is None:
                return Response(
                    {"error": "Assignment not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Get active employee assignments
            active_assignments = EmployeeAssignment.objects.filter(
                assignment_group=assignment,
                status='active'
            ).select_related('employee')

            response_data = {
                "can_end": assignment.is_active,
                "is_active": assignment.is_active,
                "active_employees": active_assignments.count(),
                "active_employee_list": [
                    {
                        "id": assign.employee.id,
                        "name": assign.employee.name,
                        "assignment_date": assign.assigned_date.strftime("%Y-%m-%d")
                    }
                    for assign in active_assignments
                ],
                "start_date": assignment.created_date.strftime("%Y-%m-%d"),
                "current_status": "Active" if assignment.is_active else "Ended",
                "notes": assignment.notes
            }

            if not assignment.is_active:
                response_data["end_date"] = assignment.end_date.strftime("%Y-%m-%d") if assignment.end_date else None

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AttendanceListCreateView(generics.ListCreateAPIView):
    queryset = Attendance.objects.all().order_by('-id')
    serializer_class = AttendanceSerializer

class AttendanceRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    lookup_url_kwarg = 'attendance_id'

class MarkAttendanceView(APIView):
    permission_classes = [AllowAny]  # Allow any user to access this view
    authentication_classes = []      # No authentication required
    
    def post(self, request):
        serializer = AttendanceMarkSerializer(data=request.data)
        if serializer.is_valid():
            try:
                attendance = serializer.save()
                return Response(
                    AttendanceSerializer(attendance).data,
                    status=status.HTTP_200_OK
                )
            except Exception as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TodayAttendanceView(generics.ListAPIView):
    serializer_class = AttendanceSerializer

    def get_queryset(self):
        return Attendance.objects.filter(date=timezone.now().date())

class DepartmentAttendanceView(generics.ListAPIView):
    serializer_class = AttendanceSerializer

    def get_queryset(self):
        department_id = self.kwargs['department_id']
        return Attendance.objects.filter(
            employee_assignment__assignment_group__department_id=department_id
        )

class EmployeeAttendanceHistoryView(generics.ListAPIView):
    serializer_class = AttendanceSerializer

    def get_queryset(self):
        employee_id = self.kwargs['employee_id']
        return Attendance.objects.filter(
            employee_assignment__employee_id=employee_id
        ).order_by('-date')