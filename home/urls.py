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

    path('users/', UserListView.as_view(), name='getUsers'),
    path('user/<int:user_id>/', UserDetailView.as_view(), name='userDetail'),

    path('departments/', DepartmentListCreateView.as_view(), name='getDepartmentListCreate'),
    path('department/<int:department_id>/', DepartmentRetrieveUpdateDestroyView.as_view(), name='departmentRetrieveUpdateDestroy'),
]  + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)