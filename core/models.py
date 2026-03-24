from enum import unique
from operator import truediv
from statistics import mode
from django.db import models
from django.db.models.fields import BigAutoField
from django.utils import tree
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.conf import settings
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField
from django.contrib.auth import get_user_model
from PIL import Image
from rest_framework.serializers import BaseSerializer
from phonenumber_field.modelfields import PhoneNumberField
from django.contrib.auth.hashers import make_password, check_password, identify_hasher
from datetime import timedelta
from django.db import transaction

from django.db import models
from django.contrib.auth.models import User
class Note(models.Model):

    title  = models.CharField(max_length=255,null=True, blank=True)
    shop_title = models.CharField(max_length=255,null=True, blank=True)
    short_description = models.TextField(null=True, blank=True)
   

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete= models.SET_NULL, related_name="+", null=True, blank=True)

    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete= models.SET_NULL, related_name="+", null=True, blank=True)
    
    class Meta:
        ordering = ('title',)

    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        self.title = self.title.replace(' ', '_').upper()
        super().save(*args, **kwargs)
    
class Decision(models.Model):
    """Store questions/decisions for mental unload"""
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('resolved', 'Resolved'),
    ]
    
    MODE_CHOICES = [
        ('family', 'Family'),
        ('work', 'Work'),
        ('general', 'General'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='decisions')
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default='general')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='open')
    
    class Meta:
        db_table = 'decisions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.text[:50]}..."