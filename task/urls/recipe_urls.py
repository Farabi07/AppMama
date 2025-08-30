
from django.urls import path
from task.views import recipe_views as views


urlpatterns = [
	path('api/v1/recipe/all/', views.getAllRecipe),

	path('api/v1/recipe/without_pagination/all/', views.getAllRecipeWithoutPagination),

	path('api/v1/recipe/<int:pk>', views.getARecipe),

	path('api/v1/recipe/search/', views.searchRecipe),

	path('api/v1/recipe/create/', views.createRecipe),

	path('api/v1/recipe/update/<int:pk>', views.updateRecipe),

	path('api/v1/recipe/delete/<int:pk>', views.deleteRecipe),

]