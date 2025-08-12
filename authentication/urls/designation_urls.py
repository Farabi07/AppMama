
from django.urls import path
from authentication.views import designation_views as views


urlpatterns = [

	path('api/v1/designation/all/', views.getAllDesignation),

	path('api/v1/designation/without_pagination/all/', views.getAllDesignationWithoutPagination),

	path('api/v1/designation/<int:pk>', views.getADesignation),

	path('api/v1/designation/search/', views.searchDesignation),

	path('api/v1/designation/create/', views.createDesignation),

	path('api/v1/designation/update/<int:pk>', views.updateDesignation),

	path('api/v1/designation/delete/<int:pk>', views.deleteDesignation),

]
