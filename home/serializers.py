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
    supervisor_name = serializers.CharField(source='supervisor.name', read_only=True)
    
    class Meta:
        model = AssignmentGroup
        fields = ['id', 'name', 'field', 'field_name', 'department', 
                 'department_name', 'supervisor', 'supervisor_name',
                 'created_date', 'end_date', 'notes', 'is_active', 
                 'employee_assignments']
        read_only_fields = ['created_date']

    def validate(self, data):
        if data.get('end_date') and data['end_date'] < data.get('created_date', timezone.now().date()):
            raise serializers.ValidationError("End date cannot be before creation date")

        # Validate that supervisor is not assigned as an employee
        # if 'supervisor' in data:
        #     supervisor = data['supervisor']
        #     active_assignments = EmployeeAssignment.objects.filter(
        #         employee=supervisor,
        #         status='active'
        #     )
        #     if active_assignments.exists():
        #         raise serializers.ValidationError(
        #             {"supervisor": "This employee is currently assigned as a worker and cannot be a supervisor"}
        #         )
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
    employee_id = serializers.CharField(source='employee_assignment.employee.id', read_only=True)
    employee_name = serializers.CharField(source='employee_assignment.employee.name', read_only=True)
    department_id = serializers.CharField(
        source='employee_assignment.assignment_group.department.id', 
        read_only=True
    )
    department_name = serializers.CharField(
        source='employee_assignment.assignment_group.department.name', 
        read_only=True
    )
    is_supervisor = serializers.BooleanField(default=False)
    
    class Meta:
        model = Attendance
        fields = [
            'id', 
            'employee_id',
            'employee_name',
            'department_id', 
            'department_name', 
            'date', 
            'attended',
            'day_salary',
            'is_supervisor',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['day_salary']

class AttendanceMarkSerializer(serializers.Serializer):
    tag_ids = serializers.ListField(
        child=serializers.CharField(),
        required=True,
        allow_empty=False
    )
    date = serializers.DateField(required=False, default=timezone.now().date())

    def validate_tag_ids(self, value):
        if not value:
            raise serializers.ValidationError("At least one tag_id is required.")
        
        # Validate each tag_id individually
        for tag_id in value:
            try:
                # Check if it's a supervisor
                AssignmentGroup.objects.get(supervisor__tag_id=tag_id, is_active=True)
            except AssignmentGroup.DoesNotExist:
                # If not a supervisor, check if it's an employee
                try:
                    EmployeeAssignment.objects.get(employee__tag_id=tag_id, status='active')
                except EmployeeAssignment.DoesNotExist:
                    raise serializers.ValidationError(f"No active assignment found for tag ID {tag_id}")

        return value

    def create(self, validated_data):
        tag_ids = validated_data.get('tag_ids')
        date = validated_data.get('date')
        attendance_records = []

        for tag_id in tag_ids:
            # Determine if the tag ID is a supervisor or employee and get the respective assignment
            try:
                assignment_group = AssignmentGroup.objects.get(supervisor__tag_id=tag_id, is_active=True)
                employee_assignment = EmployeeAssignment.objects.filter(assignment_group=assignment_group).first()
                is_supervisor = True
            except AssignmentGroup.DoesNotExist:
                employee_assignment = EmployeeAssignment.objects.get(employee__tag_id=tag_id, status='active')
                is_supervisor = False

            # Check if attendance already exists for the date
            existing_attendance = Attendance.objects.filter(
                employee_assignment=employee_assignment,
                date=date
            ).first()

            if existing_attendance:
                if existing_attendance.attended:
                    raise serializers.ValidationError({
                        "attendance": f"Attendance has already been marked for tag ID {tag_id} on this date."
                    })
                existing_attendance.attended = True
                existing_attendance.save()
                attendance_records.append(existing_attendance)
            else:
                # Create a new attendance record
                attendance = Attendance.objects.create(
                    employee_assignment=employee_assignment,
                    date=date,
                    attended=True,
                    is_supervisor=is_supervisor
                )
                attendance_records.append(attendance)

        return attendance_records
