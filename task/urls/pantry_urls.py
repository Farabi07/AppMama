
from django.urls import path
from task.views import pantry_views as views


urlpatterns = [
	path('api/v1/pantry/all/', views.getAllPantry),
	path('api/v1/pantry/without_pagination/all/', views.getAllPantryWithoutPagination),

	path('api/v1/pantry/<int:pk>', views.getAPantry),

	path('api/v1/pantry/search/', views.searchPantry),

	path('api/v1/pantry/create/', views.createPantry),

	path('api/v1/pantry/update/', views.updatePantry),
	path('api/v1/pantry/delete/<int:pk>', views.deletePantry),

]