# from _typeshed import ReadableBuffer
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone 
from django.db.models import Q

from rest_framework import serializers, status
from rest_framework import response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth.hashers import make_password, check_password
from drf_spectacular.utils import OpenApiParameter, extend_schema

from authentication.decorators import has_permissions
from authentication.models import Permission
from authentication.serializers import (AdminUserSerializer, PasswordChangeSerializer, AdminUserListSerializer,UserRegistrationSerializer, UserRelationsSerializer)
from authentication.filters import UserFilter

from utils.login_logout import get_all_logged_in_users

from commons.enums import PermissionEnum
from commons.pagination import Pagination
import random
from django.core.mail import send_mail


from authentication.models import PasswordResetOTP, User, Child, Partner
from authentication.permissions import IsEmployee, IsAdmin
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail


from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.utils.timezone import now
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404

from django.contrib.auth import get_user_model


# Create your views here.
User = get_user_model()


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
	def validate(self, attrs):
		data = super().validate(attrs)

		# data['username'] = self.user.username
		# data['email'] = self.user.email

		serializer = AdminUserListSerializer(self.user).data

		for k, v in serializer.items():
			data[k] = v

		# data.pop('refresh')
		# data.pop('access')
		return data




# @permission_classes([IsAdmin])
class MyTokenObtainPairView(TokenObtainPairView):
	serializer_class = MyTokenObtainPairSerializer

	print('mytoken obtain view')
	def f():
		print('mytoken obtain view')
		pass



@extend_schema(
	parameters=[
		OpenApiParameter("page"),
		OpenApiParameter("size"),
  ],
	request=AdminUserSerializer,
	responses=AdminUserSerializer
)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_LIST.name])
def getAllUser(request):
	users = User.objects.all()
	total_elements = users.count()

	page = request.query_params.get('page')
	size = request.query_params.get('size')

	# Pagination
	pagination = Pagination()
	pagination.page = page
	pagination.size = size
	users = pagination.paginate_data(users)

	serializer = AdminUserListSerializer(users, many=True)

	response = {
		'users': serializer.data,
		'page': pagination.page,
		'size': pagination.size,
		'total_pages': pagination.total_pages,
		'total_elements': total_elements,
	}

	return Response(response, status=status.HTTP_200_OK)




@extend_schema(
	parameters=[
		OpenApiParameter("page"),
		OpenApiParameter("size"),
  ],
	request=AdminUserSerializer,
	responses=AdminUserSerializer
)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_LIST.name])
def getAllUserWithLoggedInStatus(request):
	users = User.objects.all()
	total_elements = users.count()

	logged_in_user_ids = get_all_logged_in_users()

	page = request.query_params.get('page')
	size = request.query_params.get('size')

	# Pagination
	pagination = Pagination()
	pagination.page = page
	pagination.size = size
	users = pagination.paginate_data(users)

	serializer = AdminUserListSerializer(users, many=True)

	response = {
		'users': serializer.data,
		'page': pagination.page,
		'size': pagination.size,
		'total_pages': pagination.total_pages,
		'total_elements': total_elements,
	}

	return Response(response, status=status.HTTP_200_OK)




@extend_schema(
	parameters=[
		OpenApiParameter("page"),
		OpenApiParameter("size"),
  ],
	request=AdminUserSerializer,
	responses=AdminUserSerializer
)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_LIST.name])
def getAllUserWithoutPagination(request):
	users = User.objects.all()

	serializer = AdminUserListSerializer(users, many=True)

	return Response({'users': serializer.data}, status=status.HTTP_200_OK)




@extend_schema(request=AdminUserSerializer, responses=AdminUserSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.USER_DETAILS.name])
def getAUser(request, pk):
	try:
		user = User.objects.get(pk=pk)
		serializer = AdminUserSerializer(user)
		return Response(serializer.data)
	except ObjectDoesNotExist:
		return Response({'detail': f"User id - {pk} doesn't exists"})




@extend_schema(request=AdminUserListSerializer, responses=AdminUserListSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DETAILS_VIEW.name])
def searchUser(request):
	users = UserFilter(request.GET, queryset=User.objects.all())
	users = users.qs

	print('searched_products: ', users)

	total_elements = users.count()

	page = request.query_params.get('page')
	size = request.query_params.get('size')

	# Pagination
	pagination = Pagination()
	pagination.page = page
	pagination.size = size
	users = pagination.paginate_data(users)

	serializer = AdminUserListSerializer(users, many=True)

	response = {
		'users': serializer.data,
		'page': pagination.page,
		'size': pagination.size,
		'total_pages': pagination.total_pages,
		'total_elements': total_elements,
	}

	if len(users) > 0:
		return Response(response, status=status.HTTP_200_OK)
	else:
		return Response({'detail': f"There are no users matching your search"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=AdminUserSerializer, responses=AdminUserSerializer)
@api_view(['POST'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.USER_CREATE.name])
def createUser(request):
	data = request.data

	current_datetime = timezone.now()
	current_datetime = str(current_datetime)
	print('current_datetime str: ', current_datetime)

	user_data_dict = {}

	for key, value in data.items():
		user_data_dict[key] = value
		
	user_data_dict['last_login'] = current_datetime

	print('user_data_dict: ', user_data_dict)

	serializer = AdminUserSerializer(data=user_data_dict, many=False)
	
	if serializer.is_valid():
		serializer.save()
		return Response(serializer.data, status=status.HTTP_201_CREATED)
	else:
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 7 day free trial registration
@extend_schema(request=UserRegistrationSerializer, responses=UserRegistrationSerializer)
@api_view(['POST'])
def registerUser(request):
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        send_activation_email(user, request)  # <-- Send activation email here
        return Response({"message": "User registered successfully with free 7-day trial. Please check your email to activate your account."}, status=201)
    return Response(serializer.errors, status=400)

@extend_schema(request=AdminUserSerializer, responses=AdminUserSerializer)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.USER_UPDATE.name, PermissionEnum.USER_PARTIAL_UPDATE.name])
def updateUser(request, pk):
	try:
		user = User.objects.get(pk=pk)
		data = request.data
		serializer = AdminUserSerializer(user, data=data, partial=True)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_200_OK)
		else:
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
	except ObjectDoesNotExist:
		return Response({'detail': f"User id - {pk} doesn't exists"})




@extend_schema(
	parameters=[
		OpenApiParameter("permission"),

  ],
	request=AdminUserSerializer,
	responses=AdminUserSerializer
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.USER_UPDATE.name, PermissionEnum.USER_PARTIAL_UPDATE.name])
def userHasPermission(request):
	permission_param = request.query_params.get('permission')
	user = request.user

	try:
		permission = Permission.objects.get(name=permission_param)
	except:
		response = {'detail': f"There is no such permission named '{permission_param}'."}
		return Response(response, status=status.HTTP_400_BAD_REQUEST)


	get_permission = user.role.permissions.get(pk=permission.id)

	if get_permission:
		return Response({'permission': True}, status=status.HTTP_200_OK)
	else:
		response = {'detail': f"Pemission denied! this user has no '{permission_param}' permission."}
		return Response(response, status=status.HTTP_400_BAD_REQUEST)


@permission_classes([IsAuthenticated])
@extend_schema(request=PasswordChangeSerializer)
@api_view(['PATCH'])
def userPasswordChange(request, pk):
    try:
        # Retrieve the user by pk
        user = User.objects.get(pk=pk)
        
        # Get the current password, new password, and confirm password from the request data
        data = request.data
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')

        # Check if any of the fields are missing
        if not current_password or not new_password or not confirm_password:
            return Response({'detail': 'current_password, new_password, and confirm_password are required.'},
                            status=status.HTTP_400_BAD_REQUEST)

        # Verify if the current password matches the user's existing password
        if not check_password(current_password, user.password):
            return Response({'detail': 'The current password is incorrect.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if the new password matches the confirm password
        if new_password != confirm_password:
            return Response({'detail': 'The new password and confirm password do not match.'},
                            status=status.HTTP_400_BAD_REQUEST)

        # Update the user's password
        user.password = make_password(new_password)
        user.save()

        return Response({'detail': f"User Id - {pk}'s password has been changed successfully."},
                        status=status.HTTP_200_OK)
    
    except ObjectDoesNotExist:
        return Response({'detail': f"User id - {pk} doesn't exist."}, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        return Response({'detail': f'An error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@permission_classes([IsAuthenticated])
@api_view(['PATCH'])
def userImageUpload(request, pk):
    print("FILES:", request.FILES)
    print("DATA:", request.data)
    
    try:
        user = User.objects.get(pk=pk)
        
        # Get the uploaded image from request.FILES (if present)
        image = request.FILES.get('image')
        # Get the full name from request.data (if present)
        full_name = request.data.get('full_name')
        
        # Update image if provided
        if image:
            user.image = image
        # Update full_name if provided
        if full_name:
            user.full_name = full_name

        # If neither image nor full_name is provided, return an error
        if not image and not full_name:
            response = {'detail': "Please provide either an image or a full name"}
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        # Save the user instance with the updated fields
        user.save()
        
        # Return the image URL and full name as part of the response
        response_data = {
            'image_url': user.image.url if user.image else None,
            'full_name': user.full_name
        }
        
        return Response(response_data, status=status.HTTP_200_OK)

    except ObjectDoesNotExist:
        response = {'detail': f"User id - {pk} doesn't exist"}
        return Response(response, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        response = {'detail': f'An error occurred: {str(e)}'}
        return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@extend_schema(request=AdminUserSerializer, responses=AdminUserSerializer)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@has_permissions([PermissionEnum.USER_DELETE.name])
def deleteUser(request, pk):
	try:
		user = User.objects.get(pk=pk)
		user.delete()
		return Response({'detail': f'User id - {pk} is deleted successfully'}, status=status.HTTP_200_OK)
	except ObjectDoesNotExist:
		return Response({'detail': f"User id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)






@extend_schema(request=AdminUserSerializer, responses=AdminUserSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.USER_DELETE.name])
def checkUsernameWhenCreate(request):

	username = request.query_params.get('username', None)
	print('username: ', username)
	print('type of username: ', type(username))

	response_data = {}

	if username is not None:
		user_objs = User.objects.filter(username=username)
	else:
		return Response({'detail': "Username can't be null."})

	if len(user_objs) > 0:
		response_data['username_exists'] = True
	else:
		response_data['username_exists'] = False
	
	return Response(response_data)




@extend_schema(request=AdminUserSerializer, responses=AdminUserSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.USER_DELETE.name])
def checkUsernameWhenUpdate(request):

	username = request.query_params.get('username', None)
	user = request.query_params.get('user', None)

	response_data = {}

	if username is not None:
		user_names_list = User.objects.filter(username=username).values_list('username', flat=True)
		print('user_names_list: ', user_names_list)
	else:
		return Response({'detail': "Username can't be null."})

	if user is not None:
		user_obj = User.objects.get(pk=int(user))
	else:
		return Response({'detail': "User can't be null."})

	if username == user_obj.username:
		response_data['username_exists'] = False

	elif username in user_names_list:
		response_data['username_exists'] = True
	else:
		response_data['username_exists'] = False
	
	return Response(response_data)



	
@extend_schema(request=AdminUserSerializer, responses=AdminUserSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.USER_DELETE.name])
def checkEmailWhenCreate(request):

	email = request.query_params.get('email', None)
	response_data = {}

	if email is not None:
		user_objs = User.objects.filter(email=email)
	else:
		return Response({'detail': "Email can't be null."})

	if len(user_objs) > 0:
		response_data['email_exists'] = True
	else:
		response_data['email_exists'] = False
	
	return Response(response_data)




@extend_schema(request=AdminUserSerializer, responses=AdminUserSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.USER_DELETE.name])
def checkEmailWhenUpdate(request):

	email = request.query_params.get('email', None)
	user = request.query_params.get('user', None)

	response_data = {}

	if email is not None:
		emails_list = User.objects.filter(email=email).values_list('email', flat=True)
		print('emails_list: ', emails_list)
	else:
		return Response({'detail': "Email can't be null."})

	if user is not None:
		user_obj = User.objects.get(pk=int(user))
	else:
		return Response({'detail': "User can't be null."})

	if email == user_obj.email:
		response_data['email_exists'] = False

	elif email in emails_list:
		response_data['email_exists'] = True
	else:
		response_data['email_exists'] = False
	
	return Response(response_data)




	
@extend_schema(request=AdminUserSerializer, responses=AdminUserSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.USER_DELETE.name])
def checkPrimaryPhoneWhenCreate(request):

	_primary_phone = request.query_params.get('primary_phone', None)
	_primary_phone =  str(_primary_phone).replace(' ', '')
	primary_phone = '+' + _primary_phone
	print('_primary_phone:', _primary_phone)
	print('primary_phone:', primary_phone)

	response_data = {}

	if _primary_phone is not None:
		user_objs = User.objects.filter(Q(primary_phone=primary_phone) | Q(secondary_phone=primary_phone))
		print('user_objs: ', user_objs)
	else:
		return Response({'detail': "Primary phone number can't be null."})

	if len(user_objs) > 0:
		response_data['primary_phone_exists'] = True
	else:
		response_data['primary_phone_exists'] = False
	
	return Response(response_data)




@extend_schema(request=AdminUserSerializer, responses=AdminUserSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.USER_DELETE.name])
def checkPrimaryPhoneWhenUpdate(request):

	_primary_phone = request.query_params.get('primary_phone', None)
	_primary_phone =  str(_primary_phone).replace(' ', '')
	primary_phone = '+' + _primary_phone
	print('_primary_phone:', _primary_phone)
	print('primary_phone:', primary_phone)

	user = request.query_params.get('user', None)

	response_data = {}

	primary_phones_list = []
	if _primary_phone is not None:
		_primary_phones_list = User.objects.filter(Q(primary_phone=primary_phone) | Q(secondary_phone=primary_phone)).values_list('primary_phone', 'secondary_phone')
		print('primary_phones_list: ', _primary_phones_list)
		for tup in _primary_phones_list:
			for t in tup:
				primary_phones_list.append(t)
	else:
		return Response({'detail': "Primary phone can't be null."})
	print('primary_phones_list: ', primary_phones_list)

	if user is not None:
		user_obj = User.objects.get(pk=int(user))
	else:
		return Response({'detail': "User can't be null."})

	if primary_phone == user_obj.primary_phone:
		response_data['primary_phone_exists'] = False

	elif primary_phone in primary_phones_list:
		response_data['primary_phone_exists'] = True
	else:
		response_data['primary_phone_exists'] = False
	
	return Response(response_data)



	
@extend_schema(request=AdminUserSerializer, responses=AdminUserSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.USER_DELETE.name])
def checkSecondaryPhoneWhenCreate(request):

	_secondary_phone = request.query_params.get('secondary_phone', None)
	_secondary_phone = str(_secondary_phone).replace(' ', '')
	secondary_phone = '+' + _secondary_phone
	print('_secondary_phone:', _secondary_phone)
	print('secondary_phone:', secondary_phone)

	response_data = {}

	if _secondary_phone is not None:
		user_objs = User.objects.filter(Q(primary_phone=secondary_phone) | Q(secondary_phone=secondary_phone))
	else:
		return Response({'detail': "Secondary phone number can't be null."})

	if len(user_objs) > 0:
		response_data['secondary_phone_exists'] = True
	else:
		response_data['secondary_phone_exists'] = False
	
	return Response(response_data)
	



@extend_schema(request=AdminUserSerializer, responses=AdminUserSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.USER_DELETE.name])
def checkSecondaryPhoneWhenUpdate(request):

	_secondary_phone = request.query_params.get('secondary_phone', None)
	_secondary_phone = str(_secondary_phone).replace(' ', '')
	secondary_phone = '+' + _secondary_phone
	print('_secondary_phone:', _secondary_phone)
	print('secondary_phone:', secondary_phone)

	user = request.query_params.get('user', None)

	response_data = {}

	secondary_phones_list = []
	if _secondary_phone is not None:
		_secondary_phones_list = User.objects.filter(Q(primary_phone=secondary_phone) | Q(secondary_phone=secondary_phone)).values_list('primary_phone', 'secondary_phone')
		print('secondary_phones_list: ', _secondary_phones_list)
		for tup in _secondary_phones_list:
			print('tup: ', tup)
			for t in tup:
				print('t: ', t)
				secondary_phones_list.append(t)
	else:
		return Response({'detail': "Secondary phone can't be null."})

	print('secondary_phones_list: ', secondary_phones_list)

	if user is not None:
		user_obj = User.objects.get(pk=int(user))
	else:
		return Response({'detail': "User can't be null."})

	if secondary_phone == user_obj.secondary_phone or secondary_phone == user_obj.primary_phone:
		response_data['secondary_phone_exists'] = False

	elif secondary_phone in secondary_phones_list:
		response_data['secondary_phone_exists'] = True
	else:
		response_data['secondary_phone_exists'] = False
	
	return Response(response_data)
	


@api_view(['POST'])
def sendResetOTP(request):
    email = request.data.get('email')
    user = User.objects.filter(email=email).first()
    if not user:
        return Response({'error': 'User not found'}, status=404)
    otp = str(random.randint(10000, 99999))  # 5-digit OTP
    PasswordResetOTP.objects.create(user=user, otp=otp)
    send_mail(
        'Your Password Reset OTP',
        f'Your OTP code is: {otp}',
        None,  # Uses DEFAULT_FROM_EMAIL
        [email],
    )
    return Response({'message': 'OTP sent to your email.'})



import uuid

@api_view(['POST'])
def verifyResetOTP(request):
    email = request.data.get('email')
    otp = request.data.get('otp')
    user = User.objects.filter(email=email).first()
    if not user:
        return Response({'error': 'User not found'}, status=404)
    otp_obj = PasswordResetOTP.objects.filter(user=user, otp=otp).order_by('-created_at').first()
    if not otp_obj or otp_obj.is_expired():
        return Response({'error': 'Invalid or expired OTP'}, status=400)
    # Generate a reset token and save it
    reset_token = uuid.uuid4()
    otp_obj.reset_token = reset_token
    otp_obj.save()
    return Response({
        'message': 'OTP verified. Now you can set your new password.',
        'reset_token': str(reset_token)
    })

@api_view(['POST'])
def setNewPasswordAfterOTP(request):
    reset_token = request.data.get('reset_token')
    new_password = request.data.get('new_password')
    confirm_password = request.data.get('confirm_password')
    otp_obj = PasswordResetOTP.objects.filter(reset_token=reset_token).order_by('-created_at').first()
    if not otp_obj:
        return Response({'error': 'Invalid or expired reset token'}, status=400)
    if not new_password or not confirm_password:
        return Response({'error': 'Both new_password and confirm_password are required.'}, status=400)
    if new_password != confirm_password:
        return Response({'error': 'Passwords do not match.'}, status=400)
    user = otp_obj.user
    user.set_password(new_password)
    user.save()
    otp_obj.delete()
    return Response({'message': 'Password reset successful'})

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

@api_view(['POST'])
@permission_classes([IsAuthenticated])

def logout_view(request):
    try:
        refresh_token = request.data.get("refresh")
        print("refresh_token:", refresh_token)
        if not refresh_token:
            return Response({"detail": "Refresh token required."}, status=status.HTTP_400_BAD_REQUEST)
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({"detail": "Logout successful."}, status=status.HTTP_205_RESET_CONTENT)
    except Exception as e:
        print("Logout error:", str(e))
        return Response({"detail": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)
    


def send_activation_email(user, request):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    # Build scheme + domain from the request dynamically (supports local IP)
    scheme = 'https' if request.is_secure() else 'http'
    domain = request.get_host()  # e.g. "10.0.70.145:8001"

    activation_link = f"{scheme}://{domain}/user/activate/{uid}/{token}/"

    subject = "Activate Your Account"
    html_message = render_to_string("email/activation_email.html", {
        "userName": getattr(user, 'full_name', user.username),
        "activationLink": activation_link,
        "year": now().year,
    })

    email = EmailMultiAlternatives(
        subject,
        "",  # optional plain text content
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )
    email.attach_alternative(html_message, "text/html")
    email.send()

    
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import get_user_model
from django.shortcuts import redirect

def activate_user(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        return render(request, 'email/activation_success.html')  # ✅ show success page
    else:
        return render(request, 'email/activation_failed.html')  # ❌ show error page
	

class UserRelationsView(APIView):
    permission_classes = [permissions.IsAuthenticated]  # Require login; adjust for admin-only access if needed

    def get(self, request, user_pk=None):
        # If no user_pk provided, default to the current authenticated user
        if user_pk is None:
            user = request.user
        else:
            user = get_object_or_404(User, pk=user_pk)
        
        # Optional: Check if the requester has permission to view this user's data
        # e.g., if request.user != user and not request.user.is_staff:
        #     return Response({"detail": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)
        
        partners = Partner.objects.filter(user=user)
        children = Child.objects.filter(user=user)
        
        data = {
            'user': user,
            'partners': partners,
            'children': children,
        }
        serializer = UserRelationsSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)