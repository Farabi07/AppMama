
from authentication.views import partner_views as views
from django.urls import path

urlpatterns = [
	path('api/v1/partner/all/', views.getAllPartner),

	path('api/v1/partner/without_paginaiton/all/', views.getAllPartnerWithoutPagination),

	path('api/v1/partner/<int:pk>', views.getAPartner),

	path('api/v1/partner/search/', views.searchPartner),
	
	path('api/v1/partner/create/', views.createPartner),

	path('api/v1/partner/update/<int:pk>', views.updatePartner),

	path('api/v1/partner/delete/<int:pk>', views.deletePartner),
    
	# path('api/v1/partner/login/', views.PartnerTokenObtainPairView.as_view()),
 
 	path('api/v1/partner/login/', views.PartnerLogin, name='partner-login'),
 
 	path('api/v1/user/PartnerImageUpload/<int:pk>/',views.PartnerImageUpload),
     
	path('api/v1/partner/change_password/<int:pk>/', views.partnerPasswordChange),
  
  	

]
