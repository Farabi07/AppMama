
from django.urls import path
from task.views import notifications_views as views


urlpatterns = [
	path('api/v1/notifications/', views.NotificationView.as_view()),
    
]




