
from django.urls import path
from authentication.views import country_views as views


urlpatterns = [
	path('api/v1/country/all/', views.getAllCountry),

	path('api/v1/country/without_pagination/all/', views.getAllCountryWithoutPagination),

	path('api/v1/country/<int:pk>', views.getACountry),

	path('api/v1/country/search/', views.searchCountry),

	path('api/v1/country/create/', views.createCountry),

	path('api/v1/country/update/<int:pk>', views.updateCountry),

	path('api/v1/country/delete/<int:pk>', views.deleteCountry),
]