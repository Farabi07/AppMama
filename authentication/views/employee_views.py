from django.core.exceptions import ObjectDoesNotExist

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from drf_spectacular.utils import  extend_schema, OpenApiParameter

from authentication.decorators import has_permissions
from authentication.models import Employee
from authentication.serializers import *
from authentication.filters import EmployeeFilter

from commons.enums import PermissionEnum
from commons.pagination import Pagination

from authentication.permissions import IsEmployee, IsAdmin
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView


# Create your views here.
class EmployeeTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        try:
            # Now fetch Employee by user relation, not email
            employee = Employee.objects.get(user=self.user)
            serializer = EmployeeSerializer(employee)
            for k, v in serializer.data.items():
                data[k] = v
        except Employee.DoesNotExist:
            # Optionally handle if user is not an employee
            pass
        return data
# @permission_classes([IsEmployee])
class EmployeeTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmployeeTokenObtainPairSerializer
@extend_schema(
	parameters=[
		OpenApiParameter("page"),
		
		OpenApiParameter("size"),
  ],
	request=EmployeeListSerializer,
	responses=EmployeeListSerializer
)

@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Only authenticated users can access this view
def getAllEmployee(request):
    # Debugging: Ensure that the user is authenticated
    user = request.user  # This will be the authenticated user
    print(f"Authenticated User: {user}")
    
    # Debugging: Print the logged-in user's ID or other identifiers
    print(f"User ID: {user.id}")
    
    # Filter employees for the specific user (assuming each employee is linked to a user via ForeignKey)
    employees = Employee.objects.filter(user=user)
    
    # Debugging: Print the number of employees associated with the user
    print(f"Employees found for User {user.id}: {employees.count()}")
    
    total_elements = employees.count()

    # Pagination: Ensure page and size are integers
    try:
        page = int(request.query_params.get('page', 1))  # Default to 1 if page is not provided
        size = int(request.query_params.get('size', 10))  # Default to 10 if size is not provided
    except ValueError:
        return Response(
            {"detail": "Page and size must be integers."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Debugging: Check the pagination values
    print(f"Pagination - Page: {page}, Size: {size}")

    # Pagination
    pagination = Pagination()
    pagination.page = page
    pagination.size = size

    # Apply pagination
    employees = pagination.paginate_data(employees)

    # Debugging: Check the number of employees after pagination
    print(f"Employees after pagination: {len(employees)}")

    # Serialize the filtered employee data
    serializer = EmployeeListSerializer(employees, many=True)

    # Prepare the response data
    response = {
        'employees': serializer.data,
        'page': pagination.page,
        'size': pagination.size,
        'total_pages': pagination.total_pages,
        'total_elements': total_elements,
    }

    # Debugging: Print the response before returning it
    print(f"Response data: {response}")

    return Response(response, status=status.HTTP_200_OK)



@extend_schema(
	parameters=[
		OpenApiParameter("page"),
		OpenApiParameter("size"),
  ],
	request=EmployeeSerializer,
	responses=EmployeeSerializer
)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_LIST_VIEW.name])
def getAllEmployeeWithoutPagination(request):
	employees = Employee.objects.all()

	serializer = EmployeeListSerializer(employees, many=True)

	return Response({'employees': serializer.data}, status=status.HTTP_200_OK)




@extend_schema(request=EmployeeSerializer, responses=EmployeeSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DETAILS_VIEW.name])
def getAEmployee(request, pk):
	try:
		Employee = Employee.objects.get(pk=pk)
		serializer = EmployeeSerializer(Employee)
		return Response(serializer.data, status=status.HTTP_200_OK)
	except ObjectDoesNotExist:
		return Response({'detail': f"Employee id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=EmployeeSerializer, responses=EmployeeSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DETAILS_VIEW.name])
def searchEmployee(request):
	employees = EmployeeFilter(request.GET, queryset=Employee.objects.all())
	employees = employees.qs

	print('searched_products: ', employees)

	total_elements = employees.count()

	page = request.query_params.get('page')
	size = request.query_params.get('size')

	# Pagination
	pagination = Pagination()
	pagination.page = page
	pagination.size = size
	employees = pagination.paginate_data(employees)

	serializer = EmployeeListSerializer(employees, many=True)

	response = {
		'employees': serializer.data,
		'page': pagination.page,
		'size': pagination.size,
		'total_pages': pagination.total_pages,
		'total_elements': total_elements,
	}

	if len(employees) > 0:
		return Response(response, status=status.HTTP_200_OK)
	else:
		return Response({'detail': f"There are no employees matching your search"}, status=status.HTTP_400_BAD_REQUEST)








@extend_schema(request=EmployeeSerializer, responses=EmployeeSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])  # Only authenticated users can create employees
def createEmployee(request):
    data = request.data
    filtered_data = {}

    # Filter out empty or '0' values
    for key, value in data.items():
        if value != '' and value != '0':
            filtered_data[key] = value

    # Pass the request context to the serializer (this will give access to request.user)
    serializer = EmployeeSerializer(data=filtered_data, context={'request': request})

    if serializer.is_valid():
        # Now calling save() will pass the request context as expected
        serializer.save()  # This will use the create method of the serializer
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(request=EmployeeSerializer, responses=EmployeeSerializer)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_UPDATE.name, PermissionEnum.PERMISSION_PARTIAL_UPDATE.name])
def updateEmployee(request,pk):
	try:
		Employee = Employee.objects.get(pk=pk)
		data = request.data
		serializer = EmployeeSerializer(Employee, data=data)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_200_OK)
		else:
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
	except ObjectDoesNotExist:
		return Response({'detail': f"Employee id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=EmployeeSerializer, responses=EmployeeSerializer)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DELETE.name])
def deleteEmployee(request, pk):
	try:
		employee = Employee.objects.get(pk=pk)
		employee.delete()
		return Response({'detail': f'Employee id - {pk} is deleted successfully'}, status=status.HTTP_200_OK)
	except ObjectDoesNotExist:
		return Response({'detail': f"Employee id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def employeeImageUpload(request, pk):
    print("FILES:", request.FILES)
    print("DATA:", request.data)
    try:
        employee = Employee.objects.get(pk=pk)
        # Use request.FILES for file uploads
        image = request.FILES.get('image')
        if image:
            employee.image = image
            employee.save()
            return Response(employee.image.url, status=status.HTTP_200_OK)
        else:
            response = {'detail': "Please upload a valid image"}
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
    except ObjectDoesNotExist:
        response = {'detail': f"User id - {pk} doesn't exists"}
        return Response(response, status=status.HTTP_400_BAD_REQUEST)
    
from rest_framework_simplejwt.tokens import RefreshToken

@api_view(['POST'])
def employeeLogin(request):
    email = request.data.get('email')
    password = request.data.get('password')

    if not email or not password:
        return Response({"error": "Email and password are required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        employee = Employee.objects.get(email=email)

        if not employee.password:
            return Response({"error": "No password set for this employee"}, status=status.HTTP_400_BAD_REQUEST)

        if not check_password(password, employee.password):
            return Response({"error": "Incorrect password"}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Use the actual User instance
        if not employee.user:
            return Response({"error": "Employee is not linked to a user"}, status=status.HTTP_400_BAD_REQUEST)

        refresh = RefreshToken.for_user(employee.user)  # ✅ Corrected
        access_token = str(refresh.access_token)

        return Response({
            'access': access_token,
            'refresh': str(refresh),
            'id': employee.id,
            'role': employee.role,
            'name': employee.name,
            'email': employee.email,
            'image': employee.image.url if employee.image else None,
        }, status=status.HTTP_200_OK)

    except Employee.DoesNotExist:
        return Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)



