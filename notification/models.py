from django.utils import timezone
from django.db import models
from task.models import Task
from django.conf import settings
from authentication.models import Child, Partner


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    partner = models.ForeignKey(Partner, null=True, blank=True, on_delete=models.CASCADE, related_name='partner_notifications')
    child = models.ForeignKey(Child, null=True, blank=True, on_delete=models.CASCADE, related_name='child_notifications')
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='notifications_task', null=True, blank=True)
    message = models.TextField()
    read = models.BooleanField(default=False)  # Whether the notification is read by the user
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    create_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='notification_created_by', on_delete=models.SET_NULL, null=True)
    update_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='notification_updated_by', on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Notification for {self.user} regarding task {self.task.task_name}"
