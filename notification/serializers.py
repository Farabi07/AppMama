from rest_framework import serializers
from notification.models import *
from django.contrib.auth import get_user_model
from django.conf import settings

from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from django_currentuser.middleware import (get_current_authenticated_user, get_current_user)

from djoser.serializers import UserCreateSerializer

from authentication.models import *
from django.utils.translation import gettext_lazy as _
from authentication.models import User
from djoser import signals
from django.core.mail import send_mail
from django.template.loader import render_to_string
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'task', 'message', 'read', 'created_at', 'updated_at']


class ContactListSerializer(serializers.ModelSerializer):
	created_by = serializers.SerializerMethodField()
	updated_by = serializers.SerializerMethodField()
	class Meta:
		model = Contact
		fields = '__all__'

	def get_created_by(self, obj):
		return obj.created_by.email if obj.created_by else obj.created_by
		
	def get_updated_by(self, obj):
		return obj.updated_by.email if obj.updated_by else obj.updated_by




class ContactMinimalListSerializer(serializers.ModelSerializer):
	class Meta:
		model = Contact
		fields = ['id', 'name']


class ContactSerializer(serializers.ModelSerializer):
	class Meta:
		model = Contact
		fields = '__all__'
	
	def create(self, validated_data):
		modelObject = super().create(validated_data=validated_data)
		user = get_current_authenticated_user()
		if user is not None:
			modelObject.created_by = user
		modelObject.save()
		return modelObject
	
	def update(self, instance, validated_data):
		modelObject = super().update(instance=instance, validated_data=validated_data)
		user = get_current_authenticated_user()
		if user is not None:
			modelObject.updated_by = user
		modelObject.save()
		return modelObject
