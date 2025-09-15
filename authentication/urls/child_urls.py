
from authentication.views import child_views as views
from django.urls import path

urlpatterns = [
	path('api/v1/child/all/', views.getAllChild),

	path('api/v1/child/without_paginaiton/all/', views.getAllChildWithoutPagination),

	path('api/v1/child/<int:pk>', views.getAChild),

	path('api/v1/child/search/', views.searchChild),
	
	path('api/v1/child/create/', views.createChild),

	path('api/v1/child/update/<int:pk>', views.updateChild),

	path('api/v1/child/delete/<int:pk>', views.deleteChild),
    
	# path('api/v1/child/login/', views.ChildTokenObtainPairView.as_view()),
 
 	path('api/v1/child/login/', views.ChildLogin, name='child-login'),
 
 	path('api/v1/user/ChildImageUpload/<int:pk>/',views.ChildImageUpload),

	path('api/v1/child/change_password/<int:pk>/', views.childPasswordChange),

]
