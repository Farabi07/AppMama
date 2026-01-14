from django.contrib.auth import get_user_model
from django.conf import settings

from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from django_currentuser.middleware import (get_current_authenticated_user, get_current_user)

from djoser.serializers import UserCreateSerializer

from core.models import Note
from task.models import *
from django.utils.translation import gettext_lazy as _
from authentication.models import User
from djoser import signals
from django.core.mail import send_mail
from django.template.loader import render_to_string


class TaskListSerializer(serializers.ModelSerializer):

	created_by = serializers.SerializerMethodField()
	updated_by = serializers.SerializerMethodField()
	class Meta:
		model = Task
		fields = '__all__'
	def get_created_by(self, obj):
		return obj.created_by.email if obj.created_by else obj.created_by
		
	def get_updated_by(self, obj):
		return obj.updated_by.email if obj.updated_by else obj.updated_by

class TaskMinimalListSerializer(serializers.ModelSerializer):
	class Meta:
		model = Task
		fields = ['id', 'name']

class TaskSerializer(serializers.ModelSerializer):
	class Meta:
		model = Task
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
	
class RecipeListSerializer(serializers.ModelSerializer):

	created_by = serializers.SerializerMethodField()
	updated_by = serializers.SerializerMethodField()
	class Meta:
		model = Recipe
		fields = '__all__'

	def get_created_by(self, obj):
		return obj.created_by.email if obj.created_by else obj.created_by
		
	def get_updated_by(self, obj):
		return obj.updated_by.email if obj.updated_by else obj.updated_by

class RecipeMinimalListSerializer(serializers.ModelSerializer):
	class Meta:
		model = Recipe
		fields = ['id', 'name']


class RecipeSerializer(serializers.ModelSerializer):
	class Meta:
		model = Recipe
		fields = '__all__'
		extra_kwargs = {
            'meal_type': {'required': False, 'allow_blank': True, 'allow_null': True}
        }
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
	

class ClientListSerializer(serializers.ModelSerializer):
	created_by = serializers.SerializerMethodField()
	updated_by = serializers.SerializerMethodField()
	class Meta:
		model = Client
		fields = '__all__'

	def get_created_by(self, obj):
		return obj.created_by.email if obj.created_by else obj.created_by
		
	def get_updated_by(self, obj):
		return obj.updated_by.email if obj.updated_by else obj.updated_by

class ClientMinimalListSerializer(serializers.ModelSerializer):
	class Meta:
		model = Client
		fields = ['id', 'name']


class ClientSerializer(serializers.ModelSerializer):
	class Meta:
		model = Client
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
	

class ReceiptListSerializer(serializers.ModelSerializer):
	created_by = serializers.SerializerMethodField()
	updated_by = serializers.SerializerMethodField()
	class Meta:
		model = Receipt
		fields = '__all__'

	def get_created_by(self, obj):
		return obj.created_by.email if obj.created_by else obj.created_by
		
	def get_updated_by(self, obj):
		return obj.updated_by.email if obj.updated_by else obj.updated_by

class ReceiptMinimalListSerializer(serializers.ModelSerializer):
	class Meta:
		model = Receipt
		fields = ['id', 'name']

class ReceiptCustomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Receipt
        fields = ['id', 'receipt_type', 'date', 'time', 'shop_name', 'address', 'payment_method', 'items', 'services', 
                  'vat_percentage', 'vat_amount', 'subtotal', 'tax', 'discount', 'total_cost']  # Specify only the required fields

    # If you want to exclude 'extracted_data' and handle it in the view, don't include it in the serializer
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Optionally, handle removing fields or modify data here
        return representation
class ReceiptSerializer(serializers.ModelSerializer):
	class Meta:
		model = Receipt
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
	def to_representation(self, instance):
		representation = super().to_representation(instance)
		representation.pop('extracted_data', None)  # Remove 'extracted_data' from the response
		return representation



class QRTaskDataListSerializer(serializers.ModelSerializer):

	created_by = serializers.SerializerMethodField()
	updated_by = serializers.SerializerMethodField()
	class Meta:
		model = QRTaskData
		fields = '__all__'

class QRTaskDataMinimalListSerializer(serializers.ModelSerializer):
	class Meta:
		model = QRTaskData
		fields = ['id', 'title']

class QRTaskDataSerializer(serializers.ModelSerializer):
    task_metadata = TaskSerializer(required=False)

    class Meta:
        model = QRTaskData
        fields = '__all__'

    def create(self, validated_data):
        task_metadata_data = validated_data.pop('task_metadata', None)

        qr_task = QRTaskData.objects.create(**validated_data)

        user = get_current_authenticated_user()
        if user:
            qr_task.created_by = user
            qr_task.save()

        if task_metadata_data:
            task_metadata = Task.objects.create(**task_metadata_data)
            qr_task.task_metadata = task_metadata
            qr_task.save()

        return qr_task

    def update(self, instance, validated_data):
        task_metadata_data = validated_data.pop('task_metadata', None)

        # update QRTaskData fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        user = get_current_authenticated_user()
        if user:
            instance.updated_by = user

        instance.save()

        if task_metadata_data:
            if instance.task_metadata:
                # update existing TaskMetadata
                for attr, value in task_metadata_data.items():
                    setattr(instance.task_metadata, attr, value)
                instance.task_metadata.save()
            else:
                # create new TaskMetadata
                task_metadata = Task.objects.create(**task_metadata_data)
                instance.task_metadata = task_metadata
                instance.save()

        return instance
	

class PeptalkListSerializer(serializers.ModelSerializer):
	
	created_by = serializers.SerializerMethodField()
	updated_by = serializers.SerializerMethodField()
	class Meta:
		model = PeptalkData
		fields = '__all__'

	def get_created_by(self, obj):
		return obj.created_by.email if obj.created_by else obj.created_by
		
	def get_updated_by(self, obj):
		return obj.updated_by.email if obj.updated_by else obj.updated_by
class PeptalkMinimalListSerializer(serializers.ModelSerializer):
	class Meta:
		model = PeptalkData
		fields = ['id', 'name']

class PeptalkSerializer(serializers.ModelSerializer):
	class Meta:
		model = PeptalkData
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
	
class PantryListSerializer(serializers.ModelSerializer):
	created_by = serializers.SerializerMethodField()
	updated_by = serializers.SerializerMethodField()
	class Meta:
		model = Pantry
		fields = '__all__'

	def get_created_by(self, obj):
		return obj.created_by.email if obj.created_by else obj.created_by
		
	def get_updated_by(self, obj):
		return obj.updated_by.email if obj.updated_by else obj.updated_by




class PantryMinimalSerializer(serializers.ModelSerializer):
	class Meta:
		model = Pantry
		fields = ['quantity', 'name']




class PantrySerializer(serializers.ModelSerializer):
	class Meta:
		model = Pantry
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
	
class NoteListSerializer(serializers.ModelSerializer):
	created_by = serializers.SerializerMethodField()
	updated_by = serializers.SerializerMethodField()
	class Meta:
		model = Note
		fields = '__all__'

	def get_created_by(self, obj):
		return obj.created_by.email if obj.created_by else obj.created_by
		
	def get_updated_by(self, obj):
		return obj.updated_by.email if obj.updated_by else obj.updated_by




class NoteMinimalListSerializer(serializers.ModelSerializer):
	class Meta:
		model = Note
		fields = ['id', 'name']


class NoteSerializer(serializers.ModelSerializer):
	class Meta:
		model = Note
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
