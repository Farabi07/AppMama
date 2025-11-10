
from django.urls import path
from notification.views import notifications as views


urlpatterns = [
	# path('api/v1/contacts/all/', views.getAllContact),

	# path('api/v1/contacts/without_pagination/all/', views.getAllContactWithoutPagination),

	# path('api/v1/contacts/<int:pk>', views.getAContact),

	# path('api/v1/contacts/search/', views.searchContact),

	# path('api/v1/contacts/create/', views.createContact),

	# path('api/v1/contacts/update/<int:pk>', views.updateContact),

	# path('api/v1/contacts/delete/<int:pk>', views.deleteContact),
    path('api/v1/notifications/', views.NotificationView.as_view()),
    path('api/mark-read/<int:notification_id>/', views.mark_notification_as_read),
    path('api/v1/unseen_notifications/list/', views.get_unseen_notifications, name='list-notifications'),
    path('api/task/reminders/', views.task_reminder_view, name='task-reminders'),
]