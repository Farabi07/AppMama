
from django.urls import path
from authentication.views import permission_views as views


urlpatterns = [
	path('api/v1/permission/all/', views.getAllPermission),

	path('api/v1/permission/without_pagination/all/', views.getAllPermissionWithoutPagination),

	path('api/v1/permission/<int:pk>', views.getAPermission),

	path('api/v1/permission/search/', views.searchPermission),

	path('api/v1/permission/create/', views.createPermission),

	path('api/v1/permission/update/<int:pk>', views.updatePermission),

	path('api/v1/permission/delete/<int:pk>', views.deletePermission),



]