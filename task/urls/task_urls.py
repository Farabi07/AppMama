
from django.urls import path
from task.views import task_views as views


urlpatterns = [
	path('api/v1/task/all/', views.getAllTask),

	path('api/v1/task/without_pagination/all/', views.getAllTaskWithoutPagination),

	path('api/v1/task/<int:pk>', views.getATask),

	path('api/v1/task/search/', views.searchTask),

	path('api/v1/task/create/', views.createTask),

	path('api/v1/task/update/<int:pk>', views.updateTask),

	path('api/v1/task/delete/<int:pk>', views.deleteTask),



]