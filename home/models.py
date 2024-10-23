from django.db import models

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

class EmployeeAssignment(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="assignments")
    field = models.ForeignKey(Field, on_delete=models.CASCADE, related_name="field_assignments")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="department_assignments")
    assigned_date = models.DateField(auto_now_add=True)  # Automatically set the date when assigned
    end_date = models.DateField(null=True, blank=True)  # Optional field to track the end of the assignment

    class Meta:
        unique_together = ['employee', 'field', 'department']  # Ensure an employee can only be assigned to one department and field at a time.

    def __str__(self):
        return f"{self.employee.name} assigned to {self.field.name} in {self.department.name}"