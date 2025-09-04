from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from task.serializers import QRTaskDataSerializer
import qrcode
import io
import base64
import json
from rest_framework.parsers import JSONParser

@api_view(['POST'])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def createQRTaskData(request):
    serializer = QRTaskDataSerializer(data=request.data)
    if serializer.is_valid():
        qr_task = serializer.save()

        # Prepare QR content
        qr_content = {
            "title": qr_task.title,
            "contents": qr_task.contents,
            "task_metadata": {
                "id": qr_task.task_metadata.id,
                "title": qr_task.task_metadata.title if qr_task.task_metadata else None
            },
            "voice_url": request.build_absolute_uri(qr_task.voice.url) if qr_task.voice else None
        }

        # Generate QR code image
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(json.dumps(qr_content))
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')

        # Convert image to base64
        buf = io.BytesIO()
        img.save(buf)
        buf.seek(0)
        qr_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')

        return Response({
            "qr_code_base64": qr_base64,
            "id": qr_task.id,
            "data": qr_content
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
