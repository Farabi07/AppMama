
from django.urls import path
from authentication.views import city_views as views


urlpatterns = [
	path('api/v1/city/all/', views.getAllCity),

	path('api/v1/city/without_pagination/all/', views.getAllCityWithoutPagination),

	path('api/v1/city/<int:pk>', views.getACity),

	path('api/v1/city/search/', views.searchCity),

	path('api/v1/city/create/', views.createCity),

	path('api/v1/city/update/<int:pk>', views.updateCity),

	path('api/v1/city/delete/<int:pk>', views.deleteCity),



]