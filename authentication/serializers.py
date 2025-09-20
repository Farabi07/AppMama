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



class PermissionListSerializer(serializers.ModelSerializer):
	created_by = serializers.SerializerMethodField()
	updated_by = serializers.SerializerMethodField()
	class Meta:
		model = Permission
		fields = '__all__'

	def get_created_by(self, obj):
		return obj.created_by.email if obj.created_by else obj.created_by
		
	def get_updated_by(self, obj):
		return obj.updated_by.email if obj.updated_by else obj.updated_by




class PermissionMinimalSerializer(serializers.ModelSerializer):
	class Meta:
		model = Permission
		fields = ['id', 'name']




class PermissionSerializer(serializers.ModelSerializer):
	class Meta:
		model = Permission
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




class RoleListSerializer(serializers.ModelSerializer):
	created_by = serializers.SerializerMethodField()
	updated_by = serializers.SerializerMethodField()
	class Meta:
		model = Role
		fields = '__all__'

	def get_created_by(self, obj):
		return obj.created_by.email if obj.created_by else obj.created_by
		
	def get_updated_by(self, obj):
		return obj.updated_by.email if obj.updated_by else obj.updated_by




class RoleMinimalListSerializer(serializers.ModelSerializer):
	class Meta:
		model = Role
		fields = ['id', 'name']


class RoleSerializer(serializers.ModelSerializer):
	class Meta:
		model = Role
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




class DesignationListSerializer(serializers.ModelSerializer):
	created_by = serializers.SerializerMethodField()
	updated_by = serializers.SerializerMethodField()
	class Meta:
		model = Designation
		fields = '__all__'

	def get_created_by(self, obj):
		return obj.created_by.email if obj.created_by else obj.created_by
		
	def get_updated_by(self, obj):
		return obj.updated_by.email if obj.updated_by else obj.updated_by




class DesignationMinimalListSerializer(serializers.ModelSerializer):
	class Meta:
		model = Designation
		fields = ['id', 'name']


class DesignationSerializer(serializers.ModelSerializer):
	class Meta:
		model = Designation
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


# Djoser user serializer used in settings.py
class UserSerializer(UserCreateSerializer):
	class Meta(UserCreateSerializer.Meta):
		model = User
		fields = ('id', 'email', 'first_name', 'last_name', 'password')


# Don't delete it
class AdminUserListSerializer(serializers.ModelSerializer):
	# role = serializers.SerializerMethodField()
	city = serializers.SerializerMethodField()
	country = serializers.SerializerMethodField()
	created_by = serializers.SerializerMethodField()
	updated_by = serializers.SerializerMethodField()
	
	class Meta:
		model = User
		exclude = ['password']
	
	# def get_role(self, obj):
	# 	return obj.role.name if obj.role else obj.role
	
	def get_city(self, obj):
		return obj.city.name if obj.city else obj.city
	
	def get_country(self, obj):
		return obj.country.name if obj.country else obj.country
	
	def get_created_by(self, obj):
		return obj.created_by.email if obj.created_by else obj.created_by
		
	def get_updated_by(self, obj):
		return obj.updated_by.email if obj.updated_by else obj.updated_by


class AdminUserMinimalListSerializer(serializers.ModelSerializer):
	image = serializers.SerializerMethodField()
	class Meta:
		model = User
		fields = ['id', 'email', 'first_name', 'last_name', 'username', 'image']

	def get_image(self, obj):
		return str(settings.MEDIA_URL) + str(obj.image) if obj.image else None


class AdminUserListSerializerForGeneralUse(serializers.ModelSerializer):

	city = serializers.SerializerMethodField()
	country = serializers.SerializerMethodField()
	created_by = serializers.SerializerMethodField()
	updated_by = serializers.SerializerMethodField()
	
	class Meta:
		model = User
		exclude = ['password', 'role', 'user_type', 'last_login']
	
	
	def get_city(self, obj):
		return obj.city.name if obj.city else obj.city
	
	def get_country(self, obj):
		return obj.country.name if obj.country else obj.country
	
	def get_created_by(self, obj):
		return obj.created_by.email if obj.created_by else obj.created_by
		
	def get_updated_by(self, obj):
		return obj.updated_by.email if obj.updated_by else obj.updated_by


class AdminUserSerializer(serializers.ModelSerializer):
	class Meta:
		model = User
		fields = '__all__'

		extra_kwargs = {
			'password': {
				'write_only': True,
				'required': False,
			},
		}

	def create(self, validated_data):
		modelObject = super().create(validated_data=validated_data)
		modelObject.set_password(validated_data["password"])
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

class CountryListSerializer(serializers.ModelSerializer):
	created_by = AdminUserMinimalListSerializer()
	updated_by = AdminUserMinimalListSerializer()
	class Meta:
		model = Country
		fields = '__all__'

class CountryMinimalListSerializer(serializers.ModelSerializer):
	class Meta:
		model = Country
		fields = ['id', 'name']


class CountrySerializer(serializers.ModelSerializer):
	class Meta:
		model = Country
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


class CityListSerializer(serializers.ModelSerializer):
	country = CountryMinimalListSerializer()
	created_by = AdminUserMinimalListSerializer()
	updated_by = AdminUserMinimalListSerializer()
	class Meta:
		model = City
		fields = '__all__'

class CityMinimalListSerializer(serializers.ModelSerializer):
	class Meta:
		model = City
		fields = ['id', 'name']

class CitySerializer(serializers.ModelSerializer):
	class Meta:
		model = City
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


class BranchListSerializer(serializers.ModelSerializer):
	city = CityMinimalListSerializer()
	country = CountryMinimalListSerializer()
	created_by = AdminUserMinimalListSerializer()
	updated_by = AdminUserMinimalListSerializer()
	class Meta:
		model = Branch
		fields = '__all__'

class BranchMinimalListSerializer(serializers.ModelSerializer):
	class Meta:
		model = Branch
		fields = ['id', 'name', ]
		
class BranchSerializer(serializers.ModelSerializer):
	class Meta:
		model = Branch
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

class EmployeeListSerializer(serializers.ModelSerializer):
    created_by = AdminUserMinimalListSerializer()
    updated_by = AdminUserMinimalListSerializer()
    # role = RoleMinimalListSerializer()
    designation = DesignationMinimalListSerializer()

    class Meta:
        model = Employee
        fields = '__all__'

class EmployeeMinimalListSerializer(serializers.ModelSerializer):
	class Meta:
		model = City
		fields = ['id', 'name']

from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Employee, Role, Designation

from django.contrib.auth import get_user_model
from rest_framework import serializers

from authentication.uitls import send_employee_credentials  # Import your utility

# class EmployeeSerializer(serializers.ModelSerializer):
#     password = serializers.CharField(write_only=True, required=True)
#     role = serializers.CharField(source='role.name', read_only=True)
#     designation = serializers.CharField(source='designation.name', read_only=True)

#     class Meta:
#         model = Employee
#         fields = [
#             'id', 'name', 'designation', 'email', 'phone', 'role','image',
#             'created_at', 'updated_at', 'created_by', 'updated_by', 'password'
#         ]
#         extra_kwargs = {'password': {'write_only': True}}

#     def create(self, validated_data):
#         password = validated_data.pop('password')
#         email = validated_data.get('email')
#         name = validated_data.get('name')

#         # Get or create EMPLOYEE role
#         role, _ = Role.objects.get_or_create(name__iexact='EMPLOYEE', defaults={'name': 'EMPLOYEE'})
#         validated_data['role'] = role

#         # Handle designation by name if needed (optional)
#         designation_name = self.initial_data.get('designation')
#         if designation_name:
#             designation_obj, _ = Designation.objects.get_or_create(name=designation_name)
#             validated_data['designation'] = designation_obj

#         # Check if user already exists
#         User = get_user_model()
#         user, created = User.objects.get_or_create(
#             email=email,
#             defaults={
#                 'full_name': name,
#                 'username': email,
#                 'role': role
#             }
#         )
#         if created:
#             user.set_password(password)
#             user.save()
#         else:
#             # Optionally, update password if you want to allow resetting here
#             # user.set_password(password)
#             # user.save()
#             pass

#         # Link the Employee to the User
#         employee = Employee.objects.create(user=user, **validated_data)

#         # Send credentials email
#         send_employee_credentials(email, password)

#         return employee

#     def to_representation(self, instance):
#         rep = super().to_representation(instance)
#         rep['role'] = instance.role.name if instance.role else None
#         rep['designation'] = instance.designation.name if instance.designation else None
#         return rep
    
class LoginHistoryListSerializer(serializers.ModelSerializer):
	created_by = serializers.SerializerMethodField()
	updated_by = serializers.SerializerMethodField()
	class Meta:
		model = LoginHistory
		fields = '__all__'
	
	def get_created_by(self, obj):
		return obj.created_by.email if obj.created_by else obj.created_by
		
	def get_updated_by(self, obj):
		return obj.updated_by.email if obj.updated_by else obj.updated_by




class LoginHistorySerializer(serializers.ModelSerializer):
	class Meta:
		model = LoginHistory
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


class PasswordChangeSerializer(serializers.Serializer):
	password = serializers.CharField(max_length=64)
	confirm_password = serializers.CharField(max_length=64)
	new_password = serializers.CharField(max_length=64)


# for 7days free trail user registration

# from djoser.serializers import UserCreateSerializer


# class UserRegistrationSerializer(UserCreateSerializer):
#     image = serializers.ImageField(required=False, allow_null=True)

#     class Meta(UserCreateSerializer.Meta):
#         model = User
#         fields = UserCreateSerializer.Meta.fields + ('full_name', 'image')

#     def create(self, validated_data):
#         # Set role to ADMIN or MANAGER as needed
#         role, created = Role.objects.get_or_create(
#             name__iexact='ADMIN',
#             defaults={'name': 'ADMIN'}
#         )
#         validated_data['role'] = role
#         validated_data['is_active'] = False  # Require email activation

#         # Remove image from validated_data if present (not needed at create)
#         validated_data.pop('image', None)
#         full_name = validated_data.pop('full_name', None)

#         # Let Djoser handle password, email, etc.
#         user = super().create(validated_data)
#         if full_name is not None:
#             user.full_name = full_name
#             user.save()
#         return user

#     def update(self, instance, validated_data):
#         instance.full_name = validated_data.get('full_name', instance.full_name)
#         image = validated_data.get('image', None)
#         if image is not None:
#             instance.image = image
#         password = validated_data.get('password', None)
#         if password:
#             instance.set_password(password)
#         instance.save()
#         return instance


# from rest_framework import serializers
# from django.contrib.auth import get_user_model
# from rest_framework.exceptions import ValidationError
# from django.db import IntegrityError  # Import IntegrityError for database constraint errors
# import logging

# # Logger for error logging
# logger = logging.getLogger(__name__)

# class UserRegistrationSerializer(UserCreateSerializer):
#     image = serializers.ImageField(required=False, allow_null=True)

#     class Meta(UserCreateSerializer.Meta):
#         model = User  # Use the actual user model
#         fields = UserCreateSerializer.Meta.fields + ('full_name', 'image')

#     def create(self, validated_data):
#         try:
#             # Remove image from validated_data if present (not needed at create)
#             validated_data.pop('image', None)
#             full_name = validated_data.pop('full_name', None)  # Full name is optional

#             # Set is_active to False to require email activation
#             validated_data['is_active'] = False  # User will be inactive initially

#             # Let Djoser handle standard user creation (email, password, etc.)
#             user = super().create(validated_data)

#             # If full_name is provided, update it after creating the user
#             if full_name:
#                 user.full_name = full_name
#                 user.save()

#             return user

#         except IntegrityError as e:
#             logger.error(f"IntegrityError during user creation: {e}")
#             raise ValidationError({"detail": "A user with this email already exists or other database constraints are violated."})
#         except ValueError as e:
#             logger.error(f"ValueError during user creation: {e}")
#             raise ValidationError({"detail": "Invalid data provided for user creation."})
#         except Exception as e:
#             logger.error(f"Unexpected error during user creation: {e}")
#             raise ValidationError({"detail": "An unexpected error occurred during user creation."})

#     def update(self, instance, validated_data):
#         try:
#             instance.full_name = validated_data.get('full_name', instance.full_name)
#             image = validated_data.get('image', None)
#             if image is not None:
#                 instance.image = image
#             password = validated_data.get('password', None)
#             if password:
#                 instance.set_password(password)
#             instance.save()
#             return instance

#         except IntegrityError as e:
#             logger.error(f"IntegrityError during user update: {e}")
#             raise ValidationError({"detail": "A user with this email already exists or other database constraints are violated."})
#         except ValueError as e:
#             logger.error(f"ValueError during user update: {e}")
#             raise ValidationError({"detail": "Invalid data provided for user update."})
#         except Exception as e:
#             logger.error(f"Unexpected error during user update: {e}")
#             raise ValidationError({"detail": "An unexpected error occurred during user update."})

class UserRegistrationSerializer(UserCreateSerializer):
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta(UserCreateSerializer.Meta):
        model = User  # Use the actual user model
        fields = UserCreateSerializer.Meta.fields + ('full_name', 'image')

    def create(self, validated_data):
        # Remove image from validated_data if present (not needed at create)
        validated_data.pop('image', None)
        full_name = validated_data.pop('full_name', None)  # Full name is optional

        # Set is_active to False to require email activation
        validated_data['is_active'] = False  # User will be inactive initially

        # Let Djoser handle standard user creation (email, password, etc.)
        user = super().create(validated_data)

        # If full_name is provided, update it after creating the user
        if full_name:
            user.full_name = full_name
            user.save()

        return user
    
    def update(self, instance, validated_data):
        instance.full_name = validated_data.get('full_name', instance.full_name)
        image = validated_data.get('image', None)
        if image is not None:
            instance.image = image
        password = validated_data.get('password', None)
        if password:
            instance.set_password(password)
        instance.save()
        return instance






from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .models import Employee, Designation

class EmployeeSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    designation = serializers.CharField(source='designation.name', read_only=True)

    class Meta:
        model = Employee
        fields = [
            'id', 'name', 'designation', 'email', 'phone', 'role', 'password', 'image',
            'created_at', 'updated_at', 'created_by', 'updated_by', 'user'
        ]
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        # Extract password
        password = validated_data.pop('password')
        email = validated_data.get('email')
        # name = validated_data.get('name')

        # Handle designation by name if provided (optional)
        designation_name = self.initial_data.get('designation')
        if designation_name:
            designation_obj, _ = Designation.objects.get_or_create(name=designation_name)
            validated_data['designation'] = designation_obj

        # Ensure default role
        validated_data['role'] = validated_data.get('role', 'employee')

        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None

        # Create employee without password (will set manually)
        employee = Employee(**validated_data)
        employee.password = password  # Model's save() will hash it

        if user:
            employee.user = user

        employee.save()
        send_employee_credentials(email, password)
        return employee

    def update(self, instance, validated_data):
        # Handle password update
        password = validated_data.pop('password', None)
        if password:
            instance.password = make_password(password)

        # Handle designation update
        designation_name = validated_data.get('designation')
        if designation_name:
            designation_obj, _ = Designation.objects.get_or_create(name=designation_name)
            validated_data['designation'] = designation_obj

        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['role'] = instance.role
        rep['designation'] = instance.designation.name if instance.designation else None
        return rep

class PartnerListSerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()
    updated_by = serializers.SerializerMethodField()
    # role = RoleMinimalListSerializer()
    designation = DesignationMinimalListSerializer()

    class Meta:
        model = Partner
        fields = '__all__'
        

class PartnerSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    designation = serializers.CharField(source='designation.name', read_only=True)

    class Meta:
        model = Partner
        fields = [
            'id', 'name', 'designation', 'email', 'phone', 'role', 'password', 'image',
            'created_at', 'updated_at', 'created_by', 'updated_by', 'user'
        ]
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        # Extract password
        password = validated_data.pop('password')
        email = validated_data.get('email')
        # name = validated_data.get('name')

        # Handle designation by name if provided (optional)
        designation_name = self.initial_data.get('designation')
        if designation_name:
            designation_obj, _ = Designation.objects.get_or_create(name=designation_name)
            validated_data['designation'] = designation_obj

        # Ensure default role
        validated_data['role'] = validated_data.get('role', 'partner')

        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None

        # Create employee without password (will set manually)
        partner = Partner(**validated_data)
        partner.password = password  # Model's save() will hash it

        if user:
            partner.user = user

        partner.save()
        send_employee_credentials(email, password)
        return partner

    def update(self, instance, validated_data):
        # Handle password update
        password = validated_data.pop('password', None)
        if password:
            instance.password = make_password(password)

        # Handle designation update
        designation_name = validated_data.get('designation')
        if designation_name:
            designation_obj, _ = Designation.objects.get_or_create(name=designation_name)
            validated_data['designation'] = designation_obj

        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['role'] = instance.role
        rep['designation'] = instance.designation.name if instance.designation else None
        return rep
class PartnerMinimalSerializer(serializers.ModelSerializer):
    designation = serializers.CharField(source='designation.name', read_only=True)

    class Meta:
        model = Partner
        # Keep all fields except password
        fields = [
            'id', 'name', 'designation', 'email', 'phone', 'role', 'image',
            'created_at', 'updated_at', 'created_by', 'updated_by', 'user'
        ]	
class ChildListSerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()
    updated_by = serializers.SerializerMethodField()
    designation = DesignationMinimalListSerializer()
    class Meta:
        model = Partner
        fields = '__all__'


class ChildSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    designation = serializers.CharField(source='designation.name', read_only=True)

    class Meta:
        model = Child
        fields = [
            'id', 'name', 'designation', 'email', 'phone', 'role', 'password', 'image',
            'created_at', 'updated_at', 'created_by', 'updated_by', 'user'
        ]
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        # Extract password
        password = validated_data.pop('password')
        email = validated_data.get('email')
        # name = validated_data.get('name')

        # Handle designation by name if provided (optional)
        designation_name = self.initial_data.get('designation')
        if designation_name:
            designation_obj, _ = Designation.objects.get_or_create(name=designation_name)
            validated_data['designation'] = designation_obj

        # Ensure default role
        validated_data['role'] = validated_data.get('role', 'child')

        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None

        # Create employee without password (will set manually)
        child = Child(**validated_data)
        child.password = password  # Model's save() will hash it

        if user:
            child.user = user

        child.save()
        send_employee_credentials(email, password)
        return child

    def update(self, instance, validated_data):
        # Handle password update
        password = validated_data.pop('password', None)
        if password:
            instance.password = make_password(password)

        # Handle designation update
        designation_name = validated_data.get('designation')
        if designation_name:
            designation_obj, _ = Designation.objects.get_or_create(name=designation_name)
            validated_data['designation'] = designation_obj

        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['role'] = instance.role
        rep['designation'] = instance.designation.name if instance.designation else None
        return rep

class ChildMinimalSerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()
    updated_by = serializers.SerializerMethodField()
    designation = DesignationMinimalListSerializer()
    class Meta:
        model = Child
        # Keep all fields except password
        fields = [
            'id', 'name', 'designation', 'email', 'phone', 'role', 'image',
            'created_at', 'updated_at', 'created_by', 'updated_by', 'user'
        ]

    def get_created_by(self, obj):
        return obj.created_by.email if obj.created_by else obj.created_by

    def get_updated_by(self, obj):
        return obj.updated_by.email if obj.updated_by else obj.updated_by

class UserRelationsSerializer(serializers.Serializer):
    user = serializers.SerializerMethodField()
    partners = PartnerMinimalSerializer(many=True)
    children = ChildMinimalSerializer(many=True)

    def get_user(self, obj):
        # Return basic user info (customize as needed)
        user = obj['user']
        return {
            'id': user.id,
            'username': user.username,  # Add more fields if needed (e.g., email)
            'full_name': user.full_name,
            'email': user.email,
            'gender': user.gender,
			'role': user.role,
            'image': user.image.url if user.image else None
        }

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        # Remove the token from the response if it's included
        representation.pop('refresh', None)
        representation.pop('access', None)

        return representation
