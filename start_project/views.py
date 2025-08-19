from django.http import HttpResponse

def index(request):
	return HttpResponse("Welcome to Our Task Management App!")

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.apple.views import AppleOAuth2Adapter
from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from allauth.socialaccount.providers.apple.client import AppleOAuth2Client
# from allauth.socialaccount.exceptions import OAuth2Error
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings


# ✅ Correct (latest version)
from dj_rest_auth.registration.views import SocialLoginView

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomGoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = settings.APPLE_CALLBACK_URL
    client_class = OAuth2Client

    def get_response(self):
        response = super().get_response()
        user = self.user

        # generate JWT tokens manually
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        # build user response
        user_data = {
            "refresh": str(refresh),
            "access": str(access),
            "id": user.id,
            "city": user.city if hasattr(user, 'city') else None,
            "country": user.country if hasattr(user, 'country') else None,
            "created_by": user.created_by.email if getattr(user, 'created_by', None) else None,
            "updated_by": user.updated_by.email if getattr(user, 'updated_by', None) else None,
            "last_login": user.last_login,
            "full_name": getattr(user, 'full_name', ""),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "email": user.email,
            "gender": getattr(user, 'gender', None),
            "primary_phone": getattr(user, 'primary_phone', None),
            "secondary_phone": getattr(user, 'secondary_phone', None),
            "user_type": getattr(user, 'user_type', None),
            "date_of_birth": getattr(user, 'date_of_birth', None),
            "is_active": user.is_active,
            "is_admin": user.is_superuser,
            "role": getattr(user, 'role', None),
            "street_address_one": getattr(user, 'street_address_one', None),
            "street_address_two": getattr(user, 'street_address_two', None),
            "postal_code": getattr(user, 'postal_code', None),
            "image": user.image.url if hasattr(user, 'image') and user.image else None,
            "nid": getattr(user, 'nid', None),
            "created_at": user.created_at if hasattr(user, 'created_at') else None,
            "updated_at": user.updated_at if hasattr(user, 'updated_at') else None,
        }

        return Response(user_data)



from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
import json
import jwt

User = get_user_model()

@method_decorator(csrf_exempt, name='dispatch')
class CustomAppleLogin(View):
    def post(self, request):
        try:
            # Parse request body
            data = json.loads(request.body.decode('utf-8'))
            id_token = data.get('id_token')
            email = data.get('email')
            given_name = data.get('given_name', '')
            family_name = data.get('family_name', '')
            print(f"Received id_token: {id_token[:50]}..." if id_token else "No id_token")
            
            if not id_token:
                return JsonResponse({
                    'error': 'id_token is required'
                }, status=400)
            
            # Decode JWT without verification for email extraction
            try:
                decoded_token = jwt.decode(id_token, options={"verify_signature": False})
                jwt_email = decoded_token.get('email')
                user_identifier = decoded_token.get('sub')
                print(f"JWT email: {jwt_email}")
                print(f"User identifier: {user_identifier}")
                
                # Use email from JWT if not provided in request
                if not email and jwt_email:
                    email = jwt_email
            except Exception as e:
                print(f"JWT decode error: {e}")
                return JsonResponse({
                    'error': 'Invalid id_token'
                }, status=400)

            if not email:
                return JsonResponse({
                    'error': 'Email is required'
                }, status=400)

            # Get or create user
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email,
                    'first_name': given_name,
                    'last_name': family_name,
                }
            )

            # Construct full_name based on email: use the part before '@' in the email
            if email:
                full_name = email.split('@')[0]  # Extract part before @ in the email
            else:
                full_name = f"{given_name} {family_name}".strip()

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access = refresh.access_token

            # Safely handle image field
            image_url = getattr(user, 'image', None)
            if image_url:
                image_url = user.image.url
            else:
                image_url = ""

            # Prepare response with safe serialization
            response_data = {
                'refresh': str(refresh),
                'access': str(access),
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'username': user.username,
                'last_name': user.last_name,
                'full_name': full_name,  # Use the constructed full_name
                'role': getattr(user, 'role', 'user'),
                'image': image_url,
            }

            print(f"Login successful for user: {user.email}")
            print('response_data', response_data)

            return JsonResponse(response_data, status=200)
        
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON in request body'
            }, status=400)
        
        except Exception as e:
            print(f"Unexpected error in Apple login: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'error': f'Authentication failed: {str(e)}'
            }, status=500)
from django.http import HttpResponse

def index(request):
	return HttpResponse("Welcome to Our Grocery Store!")

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.apple.views import AppleOAuth2Adapter
from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from allauth.socialaccount.providers.apple.client import AppleOAuth2Client
# from allauth.socialaccount.exceptions import OAuth2Error
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings


# ✅ Correct (latest version)
from dj_rest_auth.registration.views import SocialLoginView

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomGoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = settings.APPLE_CALLBACK_URL
    client_class = OAuth2Client

    def get_response(self):
        response = super().get_response()
        user = self.user

        # generate JWT tokens manually
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        # build user response
        user_data = {
            "refresh": str(refresh),
            "access": str(access),
            "id": user.id,
            "city": user.city if hasattr(user, 'city') else None,
            "country": user.country if hasattr(user, 'country') else None,
            "created_by": user.created_by.email if getattr(user, 'created_by', None) else None,
            "updated_by": user.updated_by.email if getattr(user, 'updated_by', None) else None,
            "last_login": user.last_login,
            "full_name": getattr(user, 'full_name', ""),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "email": user.email,
            "gender": getattr(user, 'gender', None),
            "primary_phone": getattr(user, 'primary_phone', None),
            "secondary_phone": getattr(user, 'secondary_phone', None),
            "user_type": getattr(user, 'user_type', None),
            "date_of_birth": getattr(user, 'date_of_birth', None),
            "is_active": user.is_active,
            "is_admin": user.is_superuser,
            "role": getattr(user, 'role', None),
            "street_address_one": getattr(user, 'street_address_one', None),
            "street_address_two": getattr(user, 'street_address_two', None),
            "postal_code": getattr(user, 'postal_code', None),
            "image": user.image.url if hasattr(user, 'image') and user.image else None,
            "nid": getattr(user, 'nid', None),
            "created_at": user.created_at if hasattr(user, 'created_at') else None,
            "updated_at": user.updated_at if hasattr(user, 'updated_at') else None,
        }

        return Response(user_data)



from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
import json
import jwt

User = get_user_model()

@method_decorator(csrf_exempt, name='dispatch')
class CustomAppleLogin(View):
    def post(self, request):
        try:
            # Parse request body
            data = json.loads(request.body.decode('utf-8'))
            id_token = data.get('id_token')
            email = data.get('email')
            given_name = data.get('given_name', '')
            family_name = data.get('family_name', '')
            print(f"Received id_token: {id_token[:50]}..." if id_token else "No id_token")
            
            if not id_token:
                return JsonResponse({
                    'error': 'id_token is required'
                }, status=400)
            
            # Decode JWT without verification for email extraction
            try:
                decoded_token = jwt.decode(id_token, options={"verify_signature": False})
                jwt_email = decoded_token.get('email')
                user_identifier = decoded_token.get('sub')
                print(f"JWT email: {jwt_email}")
                print(f"User identifier: {user_identifier}")
                
                # Use email from JWT if not provided in request
                if not email and jwt_email:
                    email = jwt_email
            except Exception as e:
                print(f"JWT decode error: {e}")
                return JsonResponse({
                    'error': 'Invalid id_token'
                }, status=400)

            if not email:
                return JsonResponse({
                    'error': 'Email is required'
                }, status=400)

            # Get or create user
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email,
                    'first_name': given_name,
                    'last_name': family_name,
                }
            )

            # Construct full_name based on email: use the part before '@' in the email
            if email:
                full_name = email.split('@')[0]  # Extract part before @ in the email
            else:
                full_name = f"{given_name} {family_name}".strip()

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access = refresh.access_token

            # Safely handle image field
            image_url = getattr(user, 'image', None)
            if image_url:
                image_url = user.image.url
            else:
                image_url = ""

            # Prepare response with safe serialization
            response_data = {
                'refresh': str(refresh),
                'access': str(access),
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'username': user.username,
                'last_name': user.last_name,
                'full_name': full_name,  # Use the constructed full_name
                'role': getattr(user, 'role', 'user'),
                'image': image_url,
            }

            print(f"Login successful for user: {user.email}")
            print('response_data', response_data)

            return JsonResponse(response_data, status=200)
        
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON in request body'
            }, status=400)
        
        except Exception as e:
            print(f"Unexpected error in Apple login: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'error': f'Authentication failed: {str(e)}'
            }, status=500)
from django.http import HttpResponse

def index(request):
	return HttpResponse("Welcome to Our Grocery Store!")

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.apple.views import AppleOAuth2Adapter
from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from allauth.socialaccount.providers.apple.client import AppleOAuth2Client
# from allauth.socialaccount.exceptions import OAuth2Error
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings


# ✅ Correct (latest version)
from dj_rest_auth.registration.views import SocialLoginView

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomGoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = settings.APPLE_CALLBACK_URL
    client_class = OAuth2Client

    def get_response(self):
        response = super().get_response()
        user = self.user

        # generate JWT tokens manually
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        # build user response
        user_data = {
            "refresh": str(refresh),
            "access": str(access),
            "id": user.id,
            "city": user.city if hasattr(user, 'city') else None,
            "country": user.country if hasattr(user, 'country') else None,
            "created_by": user.created_by.email if getattr(user, 'created_by', None) else None,
            "updated_by": user.updated_by.email if getattr(user, 'updated_by', None) else None,
            "last_login": user.last_login,
            "full_name": getattr(user, 'full_name', ""),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "email": user.email,
            "gender": getattr(user, 'gender', None),
            "primary_phone": getattr(user, 'primary_phone', None),
            "secondary_phone": getattr(user, 'secondary_phone', None),
            "user_type": getattr(user, 'user_type', None),
            "date_of_birth": getattr(user, 'date_of_birth', None),
            "is_active": user.is_active,
            "is_admin": user.is_superuser,
            "role": getattr(user, 'role', None),
            "street_address_one": getattr(user, 'street_address_one', None),
            "street_address_two": getattr(user, 'street_address_two', None),
            "postal_code": getattr(user, 'postal_code', None),
            "image": user.image.url if hasattr(user, 'image') and user.image else None,
            "nid": getattr(user, 'nid', None),
            "created_at": user.created_at if hasattr(user, 'created_at') else None,
            "updated_at": user.updated_at if hasattr(user, 'updated_at') else None,
        }

        return Response(user_data)



from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
import json
import jwt

User = get_user_model()

@method_decorator(csrf_exempt, name='dispatch')
class CustomAppleLogin(View):
    def post(self, request):
        try:
            # Parse request body
            data = json.loads(request.body.decode('utf-8'))
            id_token = data.get('id_token')
            email = data.get('email')
            given_name = data.get('given_name', '')
            family_name = data.get('family_name', '')
            print(f"Received id_token: {id_token[:50]}..." if id_token else "No id_token")
            
            if not id_token:
                return JsonResponse({
                    'error': 'id_token is required'
                }, status=400)
            
            # Decode JWT without verification for email extraction
            try:
                decoded_token = jwt.decode(id_token, options={"verify_signature": False})
                jwt_email = decoded_token.get('email')
                user_identifier = decoded_token.get('sub')
                print(f"JWT email: {jwt_email}")
                print(f"User identifier: {user_identifier}")
                
                # Use email from JWT if not provided in request
                if not email and jwt_email:
                    email = jwt_email
            except Exception as e:
                print(f"JWT decode error: {e}")
                return JsonResponse({
                    'error': 'Invalid id_token'
                }, status=400)

            if not email:
                return JsonResponse({
                    'error': 'Email is required'
                }, status=400)

            # Get or create user
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email,
                    'first_name': given_name,
                    'last_name': family_name,
                }
            )

            # Construct full_name based on email: use the part before '@' in the email
            if email:
                full_name = email.split('@')[0]  # Extract part before @ in the email
            else:
                full_name = f"{given_name} {family_name}".strip()

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access = refresh.access_token

            # Safely handle image field
            image_url = getattr(user, 'image', None)
            if image_url:
                image_url = user.image.url
            else:
                image_url = ""

            # Prepare response with safe serialization
            response_data = {
                'refresh': str(refresh),
                'access': str(access),
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'username': user.username,
                'last_name': user.last_name,
                'full_name': full_name,  # Use the constructed full_name
                'role': getattr(user, 'role', 'user'),
                'image': image_url,
            }

            print(f"Login successful for user: {user.email}")
            print('response_data', response_data)

            return JsonResponse(response_data, status=200)
        
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON in request body'
            }, status=400)
        
        except Exception as e:
            print(f"Unexpected error in Apple login: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'error': f'Authentication failed: {str(e)}'
            }, status=500)
