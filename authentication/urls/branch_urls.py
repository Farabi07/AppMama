
from django.urls import path
from authentication.views import branch_views as views


urlpatterns = [
	path('api/v1/branch/all/', views.getAllBranch),

	path('api/v1/branch/without_pagination/all/', views.getAllBranchWithoutPagination),

	path('api/v1/branch/<int:pk>', views.getABranch),

	path('api/v1/branch/get_a_branch_by_user_id//<int:user_id>', views.getABranchByUserId),

	path('api/v1/branch/search/', views.searchBranch),

	path('api/v1/branch/create/', views.createBranch),

	path('api/v1/branch/update/<int:pk>', views.updateBranch),

	path('api/v1/branch/delete/<int:pk>', views.deleteBranch),
]