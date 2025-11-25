import os
import io
import base64
import qrcode
from django.conf import settings
from django.core.files.base import ContentFile
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from task.serializers import QRTaskDataSerializer
from django.shortcuts import render, get_object_or_404
from task.models import QRTaskData
from django.http import HttpResponse
from datetime import datetime
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes
from drf_spectacular.utils import extend_schema, OpenApiParameter

@extend_schema(request=QRTaskDataSerializer, responses=QRTaskDataSerializer)
@permission_classes([IsAuthenticated])
@api_view(['POST'])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def createQRTaskData(request):
    data = request.data.copy()
    
    # Handle voice file upload directly. Prioritize 'voice' but fall back to 'voice_url'.
    voice_file = request.FILES.get('voice') or request.FILES.get('voice_url')
    
    # If voice_url is in task_metadata, extract it and try to copy the file
    voice_url_from_metadata = None
    if 'task_metadata' in data and isinstance(data['task_metadata'], dict):
        voice_url_from_metadata = data['task_metadata'].pop('voice_url', None)

    serializer = QRTaskDataSerializer(data=data)
    if serializer.is_valid():
        qr_task = serializer.save()
        
        # Priority 1: Use uploaded file if provided
        if voice_file:
            qr_task.voice = voice_file
            qr_task.save()
        # Priority 2: Copy from voice_url if provided
        elif voice_url_from_metadata:
            
            # Extract file path from URL (e.g., "/media/audio/tts_521c69d8.mp3" -> "audio/tts_521c69d8.mp3")
            if voice_url_from_metadata.startswith('/media/'):
                file_path = voice_url_from_metadata.replace('/media/', '')
                full_path = os.path.join(settings.MEDIA_ROOT, file_path)
                
                if os.path.exists(full_path):
                    # Copy file to voices directory
                    with open(full_path, 'rb') as f:
                        file_content = f.read()
                    qr_task.voice.save(os.path.basename(file_path), ContentFile(file_content), save=True)

        qr_content = {
            "title": qr_task.title,
            "contents": qr_task.contents,
            "task_metadata": {
                "id": qr_task.task_metadata.id if qr_task.task_metadata else None,
                "task_name": qr_task.task_metadata.task_name if qr_task.task_metadata else None,
                "scheduled_date": str(qr_task.task_metadata.scheduled_date) if qr_task.task_metadata else None,
                "priority": qr_task.task_metadata.priority if qr_task.task_metadata else None,
                "task_category": qr_task.task_metadata.task_category if qr_task.task_metadata else None
            },
            "voice_url": request.build_absolute_uri(qr_task.voice.url) if qr_task.voice else None
        }

        # Generate QR pointing to webpage
        qr_url = request.build_absolute_uri(f"/qrcode/view/{qr_task.id}/")
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        # Save QR image
        qr_dir = os.path.join(settings.MEDIA_ROOT, "qrcodes")
        os.makedirs(qr_dir, exist_ok=True)
        file_name = f"qr_task_{qr_task.id}.png"
        file_path = os.path.join(qr_dir, file_name)
        img.save(file_path)

        qr_download_url = request.build_absolute_uri(settings.MEDIA_URL + "qrcodes/" + file_name)

        buf = io.BytesIO()
        img.save(buf)
        buf.seek(0)
        qr_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        return Response({
            "id": qr_task.id,
            "data": qr_content,
            "qr_code_base64": qr_base64,
            "qr_code_url": qr_download_url,
            "qr_scan_url": qr_url
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
# @extend_schema(request=QRTaskDataSerializer, responses=QRTaskDataSerializer)
# @permission_classes([IsAuthenticated])
# @api_view(['POST'])
def qr_task_view(request, pk):
    qr_task = get_object_or_404(QRTaskData, pk=pk)
    
    data = {
        "qr_task_id": qr_task.id,  # Add QR task ID for dynamic updates
        "title": qr_task.title,
        "contents": qr_task.contents,
        "task_metadata": {
            "id": qr_task.task_metadata.id if qr_task.task_metadata else None,
            "task_name": qr_task.task_metadata.task_name if qr_task.task_metadata else None,
            "scheduled_date": qr_task.task_metadata.scheduled_date.strftime('%Y-%m-%d')
                            if qr_task.task_metadata and qr_task.task_metadata.scheduled_date else None,
            "priority": qr_task.task_metadata.priority if qr_task.task_metadata else None,
            "task_category": qr_task.task_metadata.task_category if qr_task.task_metadata else None
        },
        "voice_url": request.build_absolute_uri(qr_task.voice.url) if qr_task.voice else None
    }
    return render(request, "qr_task_view.html", {"data": data})


@api_view(['PUT', 'PATCH'])
def update_qr_task_metadata(request, pk):
    """
    Update task metadata through QR code view (no auth required for public QR access)
    """
    try:
        qr_task = QRTaskData.objects.get(pk=pk)
        if not qr_task.task_metadata:
            return Response({'error': 'No task metadata associated with this QR task'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        task = qr_task.task_metadata
        data = request.data
        
        # Update allowed fields
        if 'task_name' in data:
            task.task_name = data['task_name']
        if 'assigned_to_type' in data:
            task.assigned_to_type = data['assigned_to_type']
        if 'priority' in data:
            task.priority = data['priority']
        if 'task_category' in data:
            task.task_category = data['task_category']
        if 'scheduled_date' in data:
            task.scheduled_date = data['scheduled_date'] if data['scheduled_date'] else None
        if 'scheduled_time' in data:
            task.scheduled_time = data['scheduled_time'] if data['scheduled_time'] else None
        
        task.save()
        
        return Response({
            'id': task.id,
            'task_name': task.task_name,
            'assigned_to_type': task.assigned_to_type,
            'priority': task.priority,
            'task_category': task.task_category,
            'scheduled_date': task.scheduled_date.strftime('%Y-%m-%d') if task.scheduled_date else None,
            'scheduled_time': task.scheduled_time.strftime('%H:%M') if task.scheduled_time else None,
        }, status=status.HTTP_200_OK)
        
    except QRTaskData.DoesNotExist:
        return Response({'error': f'QR Task {pk} not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
