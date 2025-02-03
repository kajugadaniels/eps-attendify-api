from django.urls import path
from django.conf import settings
from home.views import *
from django.conf.urls.static import static

app_name = 'base'

urlpatterns = [
    path('permissions/', PermissionListView.as_view(), name='permissionList'),
    path('assign-permission/', AssignPermissionView.as_view(), name='assignPermission'),
    path('remove-permission/', RemovePermissionView.as_view(), name='removePermission'),
    path('permissions/<int:user_id>/', UserPermissionsView.as_view(), name='userPermissions'),

    path('users/', getUsers, name='getUsers'),
    path('user/<int:user_id>/', getUserDetail, name='getUserDetail'),
    path('user/<int:user_id>/update/', updateUser, name='updateUser'),
    path('user/<int:user_id>/delete/', deleteUser, name='deleteUser'),

    path('departments/', getDepartments, name='getDepartments'),
    path('department/create/', createDepartment, name='createDepartment'),
    path('department/<int:department_id>/', getDepartmentDetail, name='getDepartmentDetail'),
    path('department/<int:department_id>/update/', updateDepartment, name='updateDepartment'),
    path('department/<int:department_id>/delete/', deleteDepartment, name='deleteDepartment'),

    path('employees/', getEmployees, name='getEmployees'),
    path('employee/create/', createEmployee, name='createEmployee'),
    path('employee/<int:employee_id>/', getEmployeeDetail, name='getEmployeeDetail'),
    path('employee/<int:employee_id>/update/', updateEmployee, name='updateEmployee'),
    path('employee/<int:employee_id>/delete/', deleteEmployee, name='deleteEmployee'),

    path('fields/', FieldListCreateView.as_view(), name='getFieldListCreate'),
    path('field/<int:field_id>/', FieldRetrieveUpdateDestroyView.as_view(), name='fieldRetrieveUpdateDestroy'),

    path('assignments/', AssignmentListCreateView.as_view(), name='getAssignmentListCreate'),
    path('assignment/<int:assignment_id>/', AssignmentRetrieveUpdateDestroyView.as_view(), name='assignmentRetrieveUpdateDestroy'),
    path('assignment/<int:assignment_id>/end/', EndAssignmentView.as_view(), name='EndAssignment'),

    path('attendances/', AttendanceListCreateView.as_view(), name='getAttendanceListCreate'),
    path('attendance/<int:attendance_id>/', AttendanceRetrieveUpdateDestroyView.as_view(), name='attendanceRetrieveUpdateDestroy'),
    
    path('mark-attendance/', MarkAttendanceView.as_view(), name='markAttendance'),
    
    path('today-attendance/', TodayAttendanceView.as_view(), name='todayAttendance'),
    
    path('department-attendance/<int:department_id>/', DepartmentAttendanceView.as_view(), name='departmentAttendance'),
    
    path('employee-attendance/<int:employee_id>/', EmployeeAttendanceHistoryView.as_view(), name='employeeAttendanceHistory'),
]  + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)