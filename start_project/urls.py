"""start_project URL Configuration."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve
from drf_spectacular.views import (SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView)
from .views import CustomGoogleLogin, CustomAppleLogin
from . import views
from django.conf import settings # new
from  django.conf.urls.static import static #new
urlpatterns = [
    path('admin/', admin.site.urls),

    path('', views.index),

    # Authentication module
    path('user/', include('authentication.urls.user_urls')),
    path('employee/', include('authentication.urls.employee_urls')),
    path('partner/', include('authentication.urls.partner_urls')),
    path('child/', include('authentication.urls.child_urls')),
    path('permission/', include('authentication.urls.permission_urls')),
    path('role/', include('authentication.urls.role_urls')),
    path('designation/', include('authentication.urls.designation_urls')),

    path('country/', include('authentication.urls.country_urls')),
    path('branch/', include('authentication.urls.branch_urls')),
    path('city/', include('authentication.urls.city_urls')),
    path('subscription/', include('authentication.urls.subscription_urls')),
    path('subscriptions_plan/', include('authentication.urls.subscriptions_plan_urls')),



   
	# YOUR PATTERNS
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    # Optional UI:
    path('schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    path('djoser/auth/', include('djoser.urls')),
    path('djoser/auth/', include('djoser.urls.jwt')),
    path('auth/dj-rest-auth/', include('dj_rest_auth.urls')),
    path('auth/dj-rest-auth/registration/', include('dj_rest_auth.registration.urls')),
    # path('auth/dj-rest-auth/social/', include('allauth.socialaccount.urls')),
    path('dj-rest-auth/google/', CustomGoogleLogin.as_view(), name='google_login'),
    # path('apple/', CustomAppleLogin.as_view(), name='apple-login'),
    path('dj-rest-auth/apple/', CustomAppleLogin.as_view(), name='apple_login'),

    path('accounts/', include('allauth.urls')), 

	re_path(r'^media/(?P<path>.*)$', serve,{'document_root': settings.MEDIA_ROOT}), 
	re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]
#new
# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)
#     urlpatterns += static(settings.STATIC_URL, document_root = settings.STATIC_URL)