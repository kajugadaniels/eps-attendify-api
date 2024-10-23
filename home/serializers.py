from home.models import *
from account.models import *
from rest_framework import serializers
from django.contrib.auth.models import Permission

class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ('id', 'name', 'codename', 'content_type')

class UserSerializer(serializers.ModelSerializer):
    user_permissions = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = (
            'id', 'name', 'email', 'phone_number', 'role', 'password', 'user_permissions'
        )

    def get_user_permissions(self, obj):
        """Retrieve the user's direct permissions."""
        return obj.get_all_permissions()

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User.objects.create_user(**validated_data)
        if password:
            user.set_password(password)
        user.save()

        return user

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = (
            'id', 'name', 'day_salary'
        )

class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = (
            'id', 'name', 'email', 'phone_number', 'address', 'tag_id', 'nid', 'rssb_number'
        )

class FieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = Field
        fields = (
            'id', 'name', 'address'
        )

class EmployeeAssignmentSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.name', read_only=True)

    class Meta:
        model = EmployeeAssignment
        fields = ['id', 'employee', 'employee_name', 'assignment_group', 
                 'assigned_date', 'end_date', 'status']
        read_only_fields = ['assigned_date']

    def validate(self, data):
        if data.get('end_date') and data['end_date'] < data.get('assigned_date', timezone.now().date()):
            raise serializers.ValidationError("End date cannot be before assignment date")
        return data

class AssignmentGroupSerializer(serializers.ModelSerializer):
    employee_assignments = EmployeeAssignmentSerializer(many=True, read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    field_name = serializers.CharField(source='field.name', read_only=True)
    
    class Meta:
        model = AssignmentGroup
        fields = ['id', 'name', 'field', 'field_name', 'department', 
                 'department_name', 'created_date', 'end_date', 'notes', 
                 'is_active', 'employee_assignments']
        read_only_fields = ['created_date']

    def validate(self, data):
        if data.get('end_date') and data['end_date'] < data.get('created_date', timezone.now().date()):
            raise serializers.ValidationError("End date cannot be before creation date")
        return data

class AssignmentGroupDetailSerializer(AssignmentGroupSerializer):
    """Detailed serializer for retrieving assignment group information"""
    employee_assignments = EmployeeAssignmentSerializer(many=True, read_only=True)
    total_employees = serializers.SerializerMethodField()
    active_employees = serializers.SerializerMethodField()

    class Meta(AssignmentGroupSerializer.Meta):
        fields = AssignmentGroupSerializer.Meta.fields + ['total_employees', 'active_employees']

    def get_total_employees(self, obj):
        return obj.employee_assignments.count()

    def get_active_employees(self, obj):
        return obj.employee_assignments.filter(status='active').count()

class AttendanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee_assignment.employee.name', read_only=True)
    department_name = serializers.CharField(
        source='employee_assignment.assignment_group.department.name', 
        read_only=True
    )
    
    class Meta:
        model = Attendance
        fields = [
            'id', 
            'employee_name',
            'department_name', 
            'date', 
            'attended',
            'day_salary',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['day_salary']