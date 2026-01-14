
from django.urls import path
from task.views import note_views as views


urlpatterns = [
	path('api/v1/note/all/', views.getAllNote),

	path('api/v1/note/without_pagination/all/', views.getAllNoteWithoutPagination),

	path('api/v1/note/<int:pk>', views.getANote),

	# path('api/v1/note/search/', views.searchNote),

	path('api/v1/note/create/', views.createNote),

	path('api/v1/note/update/<int:pk>', views.updateNote),

	path('api/v1/note/delete/<int:pk>', views.deleteNote),

]