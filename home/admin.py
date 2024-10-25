from django.contrib import admin
from home.models import *

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'day_salary')
    search_fields = ('name',)

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone_number', 'tag_id', 'nid', 'rssb_number')
    search_fields = ('name', 'email', 'tag_id', 'nid', 'rssb_number')
    list_filter = ('address',)

@admin.register(Field)
class FieldAdmin(admin.ModelAdmin):
    list_display = ('name', 'address')
    search_fields = ('name',)

@admin.register(AssignmentGroup)
class AssignmentGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'supervisor', 'field', 'department', 'end_date', 'is_active')
    list_filter = ('department', 'field', 'is_active')
    search_fields = ('name', 'supervisor', 'field__name', 'department__name')

@admin.register(EmployeeAssignment)
class EmployeeAssignmentAdmin(admin.ModelAdmin):
    list_display = ('employee', 'assignment_group', 'end_date', 'status')
    list_filter = ('status', )
    search_fields = ('employee__name', 'assignment_group__name')

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee_assignment', 'date', 'attended', 'day_salary', 'created_at')
    list_filter = ('attended', 'date')
    search_fields = ('employee_assignment__employee__name', 'day_salary')
    date_hierarchy = 'date'
    readonly_fields = ('created_at', 'updated_at')

# Register all models in a structured and organized manner
