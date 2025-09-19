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

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="+", null=True, blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="+", null=True, blank=True)

    def __str__(self):
        return f"Notification for {self.user} regarding task {self.task.task_name}"


class Contact(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_contacts', null=True, blank=True)

    name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=250, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="+", null=True, blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="+", null=True, blank=True)


    def __str__(self):
        return f"{self.name} ({self.type})"
    
    class Meta:
        verbose_name = "Contact"
        verbose_name_plural = "Contacts"