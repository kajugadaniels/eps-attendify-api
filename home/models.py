from django.db import models
from django.utils import timezone
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
    notes = models.TextField(null=True, blank=True)

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
    supervisor = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="supervised_assignments", null=True)
    assigned_date = models.DateField(auto_now_add=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=ASSIGNMENT_STATUS, default='active')

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
        
        # Prevent supervisor from being assigned as an employee
        if self.supervisor:
            supervisor_assignments = EmployeeAssignment.objects.filter(
                employee=self.supervisor,
                status='active'
            ).exclude(id=self.id)
            if supervisor_assignments.exists():
                raise ValidationError(_("Supervisor cannot be assigned as an employee"))

class Attendance(models.Model):
    employee_assignment = models.ForeignKey(
        'EmployeeAssignment', 
        on_delete=models.CASCADE,
        related_name='attendances'
    )
    date = models.DateField(default=timezone.now)
    attended = models.BooleanField(default=False)
    day_salary = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['employee_assignment', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.employee_assignment.employee.name} - {self.date}"

    def save(self, *args, **kwargs):
        # Get day salary from department if not set
        if not self.day_salary:
            self.day_salary = self.employee_assignment.assignment_group.department.day_salary
        super().save(*args, **kwargs)

    def clean(self):
        # Ensure attendance is only marked for active assignments
        if self.employee_assignment.status != 'active':
            raise ValidationError(_("Cannot mark attendance for inactive assignment"))
        
        # Ensure attendance is not marked for future dates
        if self.date > timezone.now().date():
            raise ValidationError(_("Cannot mark attendance for future dates"))