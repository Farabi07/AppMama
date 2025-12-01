
from django.urls import path
from task.views import peptalk_views as views


urlpatterns = [
	path('api/v1/peptalk/all/', views.getAllPeptalkWithoutPagination),

	path('api/v1/peptalk/without_pagination/all/', views.getAllPeptalkWithoutPagination),

	path('api/v1/peptalk/<int:pk>', views.getAPeptalk),

	path('api/v1/peptalk/search/', views.searchPeptalk),

	path('api/v1/peptalk/create/', views.createPeptalk),

	path('api/v1/peptalk/update/<int:pk>', views.updatePeptalk),

	path('api/v1/peptalk/delete/<int:pk>', views.deletePeptalk),



]