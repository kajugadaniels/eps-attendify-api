from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

class Department(models.Model):
    name = models.CharField(max_length=100, null=True, blank=True)
    day_salary = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.name

class Employee(models.Model):
    name = models.CharField(max_length=100, null=True, blank=True)
    email = models.CharField(max_length=20, unique=True, null=True, blank=True)
    phone_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    address = models.CharField(max_length=20, null=True, blank=True)
    tag_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    nid = models.CharField(max_length=20, unique=True, null=True, blank=True)
    rssb_number = models.CharField(max_length=20, unique=True, null=True, blank=True)

    def __str__(self):
        return self.name

class Field(models.Model):
    name = models.CharField(max_length=100, null=True, blank=True)
    address = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.name

class AssignmentGroup(models.Model):
    name = models.CharField(max_length=100)
    field = models.ForeignKey(Field, on_delete=models.CASCADE, related_name="assignment_groups")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="assignment_groups")
    created_date = models.DateField(auto_now_add=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.field.name} ({self.department.name})"
    
    def clean(self):
        if self.end_date and self.end_date < self.created_date:
            raise ValidationError(_("End date cannot be before creation date"))

    class Meta:
        unique_together = ['name', 'field', 'department']

class EmployeeAssignment(models.Model):
    ASSIGNMENT_STATUS = (
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('suspended', 'Suspended')
    )

    assignment_group = models.ForeignKey(AssignmentGroup, on_delete=models.CASCADE, related_name="employee_assignments")
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="assignments")
    assigned_date = models.DateField(auto_now_add=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=ASSIGNMENT_STATUS, default='active')
    notes = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = ['assignment_group', 'employee']  # Prevent duplicate assignments

    def __str__(self):
        return f"{self.employee.name} in {self.assignment_group.name}"

    def clean(self):
        if self.end_date and self.end_date < self.assigned_date:
            raise ValidationError(_("End date cannot be before assignment date"))
        
        # Check if employee is already assigned to another active group
        if self.status == 'active':
            active_assignments = EmployeeAssignment.objects.filter(
                employee=self.employee,
                status='active'
            ).exclude(id=self.id)
            if active_assignments.exists():
                raise ValidationError(_("Employee is already assigned to another active group"))