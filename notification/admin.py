from django.contrib import admin
from django.contrib.auth.models import Group

from .models import *

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
	list_display = [field.name for field in Notification._meta.fields]
