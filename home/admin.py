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
    list_display = ('name', 'field', 'department', 'created_date', 'end_date', 'is_active')
    list_filter = ('department', 'field', 'is_active')
    search_fields = ('name', 'field__name', 'department__name')
    date_hierarchy = 'created_date'
    ordering = ('-created_date',)
    fieldsets = (
        (None, {
            'fields': ('name', 'field', 'department', 'is_active', 'notes')
        }),
        ('Dates', {
            'fields': ('created_date', 'end_date')
        }),
    )

@admin.register(EmployeeAssignment)
class EmployeeAssignmentAdmin(admin.ModelAdmin):
    list_display = ('employee', 'assignment_group', 'supervisor', 'assigned_date', 'end_date', 'status')
    list_filter = ('status', 'assigned_date')
    search_fields = ('employee__name', 'assignment_group__name')
    date_hierarchy = 'assigned_date'
    fieldsets = (
        (None, {
            'fields': ('employee', 'assignment_group', 'supervisor', 'status')
        }),
        ('Dates', {
            'fields': ('assigned_date', 'end_date')
        }),
    )

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee_assignment', 'date', 'attended', 'day_salary', 'created_at')
    list_filter = ('attended', 'date')
    search_fields = ('employee_assignment__employee__name', 'day_salary')
    date_hierarchy = 'date'
    readonly_fields = ('created_at', 'updated_at')

# Register all models in a structured and organized manner
