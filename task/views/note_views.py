from django.core.exceptions import ObjectDoesNotExist

from rest_framework import serializers, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from core.models import Note
from task.serializers import NoteSerializer, NoteListSerializer
# from authentication.filters import NoteFilter

from drf_spectacular.utils import  extend_schema, OpenApiParameter
from commons.pagination import Pagination

from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes


# Create your views here.

@extend_schema(
	parameters=[
		OpenApiParameter("page"),
		OpenApiParameter("size"),
  ],
	request=NoteSerializer,
	responses=NoteSerializer
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_LIST_VIEW.name])
def getAllNote(request):
    notes = Note.objects.filter(created_by=request.user)
    total_elements = notes.count()

    page = request.query_params.get('page')
    size = request.query_params.get('size')

    # Pagination
    pagination = Pagination()
    pagination.page = page
    pagination.size = size
    notes = pagination.paginate_data(notes)

    serializer = NoteListSerializer(notes, many=True)

    response = {
        'notes': serializer.data,
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
	request=NoteSerializer,
	responses=NoteSerializer
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_LIST_VIEW.name])
def getAllNoteWithoutPagination(request):
	notes = Note.objects.all()

	serializer = NoteListSerializer(notes, many=True)

	return Response({'notes': serializer.data}, status=status.HTTP_200_OK)




@extend_schema(request=NoteSerializer, responses=NoteSerializer)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getANote(request, pk):
	try:
		note = Note.objects.get(pk=pk)
		serializer = NoteSerializer(note)
		return Response(serializer.data, status=status.HTTP_200_OK)
	except ObjectDoesNotExist:
		return Response({'detail': f"Note id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)




# @extend_schema(request=NoteSerializer, responses=NoteSerializer)
# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# # @has_permissions([PermissionEnum.PRODUCT_DETAILS.name])
# def searchNote(request):

# 	notes = NoteFilter(request.GET, queryset=Note.objects.all())
# 	notes = notes.qs

# 	print('notes: ', notes)

# 	total_elements = notes.count()

# 	page = request.query_params.get('page')
# 	size = request.query_params.get('size')

# 	# Pagination
# 	pagination = Pagination()
# 	pagination.page = page
# 	pagination.size = size
# 	notes = pagination.paginate_data(notes)

# 	serializer = NoteListSerializer(notes, many=True)

# 	response = {
# 		'notes': serializer.data,
# 		'page': pagination.page,
# 		'size': pagination.size,
# 		'total_pages': pagination.total_pages,
# 		'total_elements': total_elements,
# 	}

# 	if len(notes) > 0:
# 		return Response(response, status=status.HTTP_200_OK)
# 	else:
# 		return Response({'detail': f"There are no notes matching your search"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=NoteSerializer, responses=NoteSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def createNote(request):
	data = request.data
	print('data: ', data)

	filtered_data = {}

	for key, value in data.items():
		if value != '' and value != '0':
			filtered_data[key] = value

	name = filtered_data.get('name', None)
	if name is not None:
		try:
			name = str(name).upper()
			note = Note.objects.get(name=name)
			return Response({'detail': f"Note with name '{name}' already exists."})
		except Note.DoesNotExist:
			pass

	serializer = NoteSerializer(data=filtered_data)

	if serializer.is_valid():
		serializer.save()
		return Response(serializer.data, status=status.HTTP_201_CREATED)
	else:
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=NoteSerializer, responses=NoteSerializer)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def updateNote(request,pk):
	try:
		note = Note.objects.get(pk=pk)
		data = request.data
		serializer = NoteSerializer(note, data=data)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_200_OK)
		else:
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
	except ObjectDoesNotExist:
		return Response({'detail': f"note id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=NoteSerializer, responses=NoteSerializer)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def deleteNote(request, pk):
	try:
		note = Note.objects.get(pk=pk)
		note.delete()
		return Response({'detail': f'Note id - {pk} is deleted successfully'}, status=status.HTTP_200_OK)
	except ObjectDoesNotExist:
		return Response({'detail': f"Note id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)

