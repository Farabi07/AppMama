import os
import io
import base64
import qrcode
from django.conf import settings
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from task.serializers import QRTaskDataSerializer
from django.shortcuts import render, get_object_or_404
from task.models import QRTaskData
from django.http import HttpResponse
from datetime import datetime

@api_view(['POST'])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def createQRTaskData(request):
    data = request.data.copy()

    # Convert scheduled_time if exists
    scheduled_time_str = data.get('task_metadata', {}).get('scheduled_time')
    if scheduled_time_str:
        try:
            # Convert "10:00 pm" → "22:00"
            time_obj = datetime.strptime(scheduled_time_str.strip().lower(), "%I:%M %p").time()
            data['task_metadata']['scheduled_time'] = time_obj.strftime("%H:%M:%S")
        except ValueError:
            data['task_metadata']['scheduled_time'] = None  # or raise an error

    serializer = QRTaskDataSerializer(data=data)
    if serializer.is_valid():
        qr_task = serializer.save()

        qr_content = {
            "title": qr_task.title,
            "contents": qr_task.contents,
            "task_metadata": {
                "id": qr_task.task_metadata.id if qr_task.task_metadata else None,
                "task_name": qr_task.task_metadata.task_name if qr_task.task_metadata else None,
                "scheduled_date": str(qr_task.task_metadata.scheduled_date) if qr_task.task_metadata else None,
                "scheduled_time": qr_task.task_metadata.scheduled_time.strftime("%I:%M %p") if qr_task.task_metadata and qr_task.task_metadata.scheduled_time else None,
                "priority": qr_task.task_metadata.priority if qr_task.task_metadata else None,
                "assigned_to_type": qr_task.task_metadata.assigned_to_type if qr_task.task_metadata else None
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

def qr_task_view(request, pk):
    qr_task = get_object_or_404(QRTaskData, pk=pk)
    content = {
        "title": qr_task.title,
        "contents": qr_task.contents,
        "task_metadata": {
            "id": qr_task.task_metadata.id if qr_task.task_metadata else None,
            "task_name": qr_task.task_metadata.task_name if qr_task.task_metadata else None,
            "scheduled_date": qr_task.task_metadata.scheduled_date.strftime('%Y-%m-%d')
                            if qr_task.task_metadata and qr_task.task_metadata.scheduled_date else None,
            "scheduled_time": qr_task.task_metadata.scheduled_time.strftime('%I:%M %p')
                            if qr_task.task_metadata and qr_task.task_metadata.scheduled_time else None,
            "priority": qr_task.task_metadata.priority if qr_task.task_metadata else None,
            "assigned_to_type": qr_task.task_metadata.assigned_to_type if qr_task.task_metadata else None
        },
        "voice_url": request.build_absolute_uri(qr_task.voice.url) if qr_task.voice else None
    }



    return render(request, "qr_task_view.html", {"content": content})

