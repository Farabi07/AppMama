from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from notification.models import Notification


from drf_spectacular.utils import  extend_schema, OpenApiParameter

from authentication.decorators import has_permissions
from notification.models import Contact
from notification.serializers import ContactSerializer, ContactListSerializer
from notification.filters import ContactFilter

from commons.enums import PermissionEnum
from commons.pagination import Pagination
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from notification.models import Notification
from notification.serializers import NotificationSerializer
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_unseen_notifications(request):
    notifications = Notification.objects.filter(user=request.user, read=False).order_by('-created_at')
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_as_read(request, notification_id):
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.read = True
        notification.save()
        return Response({'detail': 'Notification marked as read.'})
    except Notification.DoesNotExist:
        return Response({'error': 'Notification not found.'}, status=404)
class NotificationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # Fetch the logged-in user
        user = request.user
        
        # Check the user's role and fetch notifications accordingly
        if user.role == "child":
            # Fetch notifications for the child user
            child = user.child  # Access the child related to the user
            notifications = Notification.objects.filter(child=child, read=False)
        elif user.role == "partner":
            # Fetch notifications for the partner user
            partner = user.partner  # Access the partner related to the user
            notifications = Notification.objects.filter(partner=partner, read=False)
        elif user.role == "admin":
            # Fetch notifications for the admin user
            notifications = Notification.objects.filter(user=user, read=False)
        else:
            return Response({"error": "User role is not recognized."}, status=400)

        # Prepare notification data
        notification_data = []
        for notification in notifications:
            notification_data.append({
                "task_name": notification.task.task_name,
                "message": notification.message,
                "created_at": notification.created_at,
                "task_due_date": notification.task.scheduled_date,
                "task_due_time": notification.task.scheduled_time,
            })

        # Return the notifications to the user
        return Response({"notifications": notification_data}, status=200)
