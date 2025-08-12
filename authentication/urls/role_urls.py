
from django.urls import path
from authentication.views import role_views as views


urlpatterns = [
	path('api/v1/role/all/', views.getAllRole),

	path('api/v1/role/without_pagination/all/', views.getAllRoleWithoutPagination),

	path('api/v1/role/<int:pk>', views.getARole),

	path('api/v1/role/search/', views.searchRole),

	path('api/v1/role/create/', views.createRole),

	path('api/v1/role/update/<int:pk>', views.updateRole),

	path('api/v1/role/delete/<int:pk>', views.deleteRole),

]