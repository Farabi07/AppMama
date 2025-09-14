from authentication.views import user_views as views
from django.urls import path

urlpatterns = [
	
	path('api/v1/user/login/', views.MyTokenObtainPairView.as_view(), name='login'),

	path('api/v1/user/all/', views.getAllUser),

	path('api/v1/user/get_all_user_with_login_status/', views.getAllUserWithLoggedInStatus),

	path('api/v1/user/without_pagination/all/', views.getAllUserWithoutPagination),

	path('api/v1/user/<int:pk>', views.getAUser),

	path('api/v1/user/search/', views.searchUser),

	path('api/v1/user/create/', views.createUser),
    
	# 7 days after registration, the user will be deleted if not activated
    
	path('api/v1/register/', views.registerUser),
 
 	path('activate/<uidb64>/<token>/', views.activate_user, name='activate-user'),

	path('api/v1/user/update/<int:pk>', views.updateUser),

	path('api/v1/user/delete/<int:pk>', views.deleteUser),

	path('api/v1/user/passwordchange/<int:pk>', views.userPasswordChange),

	path('api/v1/user/uploadimage/<int:pk>/', views.userImageUpload),

	path('api/v1/user/permission/', views.userHasPermission),

	path('api/v1/user/check_username_when_create/', views.checkUsernameWhenCreate),

	path('api/v1/user/check_username_when_update/', views.checkUsernameWhenUpdate),

	path('api/v1/user/check_email_when_create/', views.checkEmailWhenCreate),

	path('api/v1/user/check_email_when_update/', views.checkEmailWhenUpdate),

	path('api/v1/user/check_primary_phone_when_create/', views.checkPrimaryPhoneWhenCreate),

	path('api/v1/user/check_primary_phone_when_update/', views.checkPrimaryPhoneWhenUpdate),

	path('api/v1/user/check_secondary_phone_when_create/', views.checkSecondaryPhoneWhenCreate),

	path('api/v1/user/check_secondary_phone_when_update/', views.checkSecondaryPhoneWhenUpdate),

    path('api/v1/send-reset-otp/', views.sendResetOTP),
    
    path('api/v1/verify-reset-otp/', views.verifyResetOTP),
    
    path('api/v1/set-new-password-after-otp/',views.setNewPasswordAfterOTP),
    
    path('logout/', views.logout_view),
    
	path('api/user-relations/', views.UserRelationsView.as_view(), name='user-relations-current'),  # For current user
    path('api/user-relations/<int:user_pk>/', views.UserRelationsView.as_view(), name='user-relations'),  # For specific user ID
]


