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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getDepartments(request):
    """
    Function-based view to list all departments.
    Only superusers or users with the 'Admin' role can view departments.
    """
    try:
        if request.user.is_superuser or request.user.role == 'Admin':
            departments = Department.objects.all().order_by('-id')
        else:
            return Response(
                {"error": "You do not have permission to view this resource."},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = DepartmentSerializer(departments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def createDepartment(request):
    """
    Function-based view to create a new department.
    Only superusers or users with the 'Admin' role can add a new department.
    """
    try:
        if not request.user.is_superuser and request.user.role != 'Admin':
            return Response(
                {"error": "You do not have permission to add a new department."},
                status=status.HTTP_403_FORBIDDEN
            )
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
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getDepartmentDetail(request, department_id):
    """
    Function-based view to retrieve details of a specific department by ID.
    """
    try:
        department = Department.objects.filter(id=department_id).first()
        if not department:
            return Response(
                {"error": "Department not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = DepartmentSerializer(department)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def updateDepartment(request, department_id):
    """
    Function-based view to update details of a specific department.
    Only superusers can update a department.
    """
    try:
        department = Department.objects.filter(id=department_id).first()
        if not department:
            return Response(
                {"error": "Department not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        if not request.user.is_superuser:
            return Response(
                {"error": "You do not have permission to update this department."},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = DepartmentSerializer(department, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Department updated successfully",
                "department": serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def deleteDepartment(request, department_id):
    """
    Function-based view to delete a specific department.
    Only superusers can delete a department.
    """
    try:
        department = Department.objects.filter(id=department_id).first()
        if not department:
            return Response(
                {"error": "Department not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        if not request.user.is_superuser:
            return Response(
                {"error": "You do not have permission to delete this department."},
                status=status.HTTP_403_FORBIDDEN
            )
        department.delete()
        return Response(
            {"message": "Department deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getEmployees(request):
    """
    Function-based view to list all employees.
    Only superusers or users with the 'Admin' role can view employees.
    """
    try:
        if request.user.is_superuser or request.user.role == 'Admin':
            employees = Employee.objects.all().order_by('-id')
        else:
            return Response(
                {"error": "You do not have permission to view this resource."},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = EmployeeSerializer(employees, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def createEmployee(request):
    """
    Function-based view to create a new employee.
    Only superusers or users with the 'Admin' role can add a new employee.
    """
    try:
        if not request.user.is_superuser and request.user.role != 'Admin':
            return Response(
                {"error": "You do not have permission to add a new employee."},
                status=status.HTTP_403_FORBIDDEN
            )
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
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getEmployeeDetail(request, employee_id):
    """
    Function-based view to retrieve details of a specific employee by ID.
    """
    try:
        employee = Employee.objects.filter(id=employee_id).first()
        if not employee:
            return Response(
                {"error": "Employee not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = EmployeeSerializer(employee)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def updateEmployee(request, employee_id):
    """
    Function-based view to update details of a specific employee.
    Only superusers can update an employee.
    """
    try:
        employee = Employee.objects.filter(id=employee_id).first()
        if not employee:
            return Response(
                {"error": "Employee not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        if not request.user.is_superuser:
            return Response(
                {"error": "You do not have permission to update this employee."},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = EmployeeSerializer(employee, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Employee updated successfully",
                "employee": serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def deleteEmployee(request, employee_id):
    """
    Function-based view to delete a specific employee.
    Only superusers can delete an employee.
    """
    try:
        employee = Employee.objects.filter(id=employee_id).first()
        if not employee:
            return Response(
                {"error": "Employee not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        if not request.user.is_superuser:
            return Response(
                {"error": "You do not have permission to delete this employee."},
                status=status.HTTP_403_FORBIDDEN
            )
        employee.delete()
        return Response(
            {"message": "Employee deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getFields(request):
    """
    Function-based view to list all fields.
    Only superusers or users with the 'Admin' role can view fields.
    """
    try:
        if request.user.is_superuser or request.user.role == 'Admin':
            fields = Field.objects.all().order_by('-id')
        else:
            return Response(
                {"error": "You do not have permission to view this resource."},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = FieldSerializer(fields, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def createField(request):
    """
    Function-based view to create a new field.
    Only superusers or users with the 'Admin' role can add a new field.
    """
    try:
        if not request.user.is_superuser and request.user.role != 'Admin':
            return Response(
                {"error": "You do not have permission to add a new field."},
                status=status.HTTP_403_FORBIDDEN
            )
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
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getFieldDetail(request, field_id):
    """
    Function-based view to retrieve details of a specific field by ID.
    """
    try:
        field = Field.objects.filter(id=field_id).first()
        if not field:
            return Response(
                {"error": "Field not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = FieldSerializer(field)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def updateField(request, field_id):
    """
    Function-based view to update details of a specific field.
    Only superusers can update a field.
    """
    try:
        field = Field.objects.filter(id=field_id).first()
        if not field:
            return Response(
                {"error": "Field not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        if not request.user.is_superuser:
            return Response(
                {"error": "You do not have permission to update this field."},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = FieldSerializer(field, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Field updated successfully",
                "field": serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def deleteField(request, field_id):
    """
    Function-based view to delete a specific field.
    Only superusers can delete a field.
    """
    try:
        field = Field.objects.filter(id=field_id).first()
        if not field:
            return Response(
                {"error": "Field not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        if not request.user.is_superuser:
            return Response(
                {"error": "You do not have permission to delete this field."},
                status=status.HTTP_403_FORBIDDEN
            )
        field.delete()
        return Response(
            {"message": "Field deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getAssignments(request):
    """
    Function-based view to list all assignment groups with detailed information.
    Only superusers or users with the 'Admin' role can view assignments.
    Supports filtering by field, department, and is_active status.
    """
    try:
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

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def createAssignment(request):
    """
    Function-based view to create a new assignment group.
    Only superusers or users with the 'Admin' role can create assignments.
    Optionally assigns employees to the group if provided.
    """
    try:
        if not (request.user.is_superuser or request.user.role == 'Admin'):
            return Response(
                {"error": "You do not have permission to create assignments."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Create the assignment group first
        group_serializer = AssignmentGroupSerializer(data=request.data)
        if not group_serializer.is_valid():
            return Response({
                "message": "Assignment group creation failed",
                "errors": group_serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        assignment_group = group_serializer.save()

        # If employees were provided, assign them to the group
        employees = request.data.get('employees', [])
        successful_assignments = []
        failed_assignments = []

        for employee_id in employees:
            try:
                EmployeeAssignment.objects.create(
                    assignment_group=assignment_group,
                    employee_id=employee_id
                )
                successful_assignments.append(employee_id)
            except Exception as e:
                failed_assignments.append({
                    "employee_id": employee_id,
                    "error": str(e)
                })

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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getAssignmentDetail(request, assignment_id):
    """
    Function-based view to retrieve detailed information about a specific assignment group.
    Only superusers or users with the 'Admin' role can view assignment details.
    """
    try:
        if not (request.user.is_superuser or request.user.role == 'Admin'):
            return Response(
                {"error": "You do not have permission to view this assignment."},
                status=status.HTTP_403_FORBIDDEN
            )

        assignment = AssignmentGroup.objects.filter(id=assignment_id).first()
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

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def updateAssignment(request, assignment_id):
    """
    Function-based view to update an existing assignment group and its employee assignments.
    Only superusers or users with the 'Admin' role can update assignments.
    """
    try:
        if not (request.user.is_superuser or request.user.role == 'Admin'):
            return Response(
                {"error": "You do not have permission to update this assignment."},
                status=status.HTTP_403_FORBIDDEN
            )

        assignment = AssignmentGroup.objects.filter(id=assignment_id).first()
        if assignment is None:
            return Response(
                {"error": "Assignment not found"},
                status=status.HTTP_404_NOT_FOUND
            )

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
                        # Log error or handle as needed; here we simply print it
                        print(f"Error adding employee {employee_id}: {str(e)}")

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

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def deleteAssignment(request, assignment_id):
    """
    Function-based view to delete an assignment group and all its employee assignments.
    Only superusers or users with the 'Admin' role can delete assignments.
    """
    try:
        if not (request.user.is_superuser or request.user.role == 'Admin'):
            return Response(
                {"error": "You do not have permission to delete this assignment."},
                status=status.HTTP_403_FORBIDDEN
            )

        assignment = AssignmentGroup.objects.filter(id=assignment_id).first()
        if assignment is None:
            return Response(
                {"error": "Assignment not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        assignment_details = AssignmentGroupDetailSerializer(assignment).data
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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getAttendances(request):
    """
    Function-based view to list all attendances.
    Returns detailed information including related employee and department data.
    """
    try:
        attendances = Attendance.objects.all().order_by('-id')
        serializer = AttendanceSerializer(attendances, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def createAttendance(request):
    """
    Function-based view to create a new attendance record.
    """
    try:
        serializer = AttendanceSerializer(data=request.data)
        if serializer.is_valid():
            attendance = serializer.save()
            return Response({
                "message": "Attendance created successfully",
                "attendance": AttendanceSerializer(attendance).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getAttendanceDetail(request, attendance_id):
    """
    Function-based view to retrieve detailed information of a specific attendance record.
    """
    try:
        attendance = Attendance.objects.filter(id=attendance_id).first()
        if not attendance:
            return Response({"error": "Attendance not found"},
                            status=status.HTTP_404_NOT_FOUND)
        serializer = AttendanceSerializer(attendance)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def updateAttendance(request, attendance_id):
    """
    Function-based view to update a specific attendance record.
    """
    try:
        attendance = Attendance.objects.filter(id=attendance_id).first()
        if not attendance:
            return Response({"error": "Attendance not found"},
                            status=status.HTTP_404_NOT_FOUND)
        serializer = AttendanceSerializer(attendance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Attendance updated successfully",
                "attendance": serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)