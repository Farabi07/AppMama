from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from notification.models import Notification

from datetime import date, timedelta
from task.models import Task

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
        user = request.user

        if user.role == "child":
            child = user.child
            notifications = Notification.objects.filter(
                child=child,
                assigned_to_type='child',
                read=False
            )
        elif user.role == "partner":
            partner = user.partner
            notifications = Notification.objects.filter(
                partner=partner,
                assigned_to_type='partner',
                read=False
            )
        elif user.role == "admin":
            notifications = Notification.objects.filter(
                user=user,
                assigned_to_type='self',
                read=False
            )
        else:
            return Response({"error": "User role is not recognized."}, status=400)

        notification_data = []
        for notification in notifications:
            notification_data.append({
                "task_name": notification.task.task_name if notification.task else "",
                "message": notification.message,
                "created_at": notification.created_at,
                "task_due_date": notification.task.scheduled_date if notification.task else "",
                "task_due_time": notification.task.scheduled_time if notification.task else "",
                "assigned_to_type": notification.assigned_to_type,
            })

        return Response({"notifications": notification_data}, status=200)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def task_reminder_view(request):
    user = request.user
    today = date.today()

    reminders = []

    # Admin/self: tasks assigned to self, due in ≤ 3 days, not completed
    if user.role == "admin":
        tasks = Task.objects.filter(
            assigned_to_type='self',
            created_by=user,
            status__in=['pending', 'in_progress'],
            scheduled_date__range=[today, today + timedelta(days=3)]
        )
        for task in tasks:
            reminders.append({
                "task_name": task.task_name,
                "due_date": task.scheduled_date,
                "due_time": task.scheduled_time,
                "days_left": (task.scheduled_date - today).days,
                "assigned_to_type": "self"
            })

    # Partner: all partner tasks, due in ≤ 2 days, not completed
    elif user.role == "partner":
        tasks = Task.objects.filter(
            assigned_to_type='partner',
            status__in=['pending', 'in_progress'],
            scheduled_date__range=[today, today + timedelta(days=2)]
        )
        for task in tasks:
            reminders.append({
                "task_name": task.task_name,
                "due_date": task.scheduled_date,
                "due_time": task.scheduled_time,
                "days_left": (task.scheduled_date - today).days,
                "assigned_to_type": "partner"
            })

    # Child: all child tasks, due in ≤ 2 days, not completed
    elif user.role == "child":
        tasks = Task.objects.filter(
            assigned_to_type='child',
            status__in=['pending', 'in_progress'],
            scheduled_date__range=[today, today + timedelta(days=2)]
        )
        for task in tasks:
            reminders.append({
                "task_name": task.task_name,
                "due_date": task.scheduled_date,
                "due_time": task.scheduled_time,
                "days_left": (task.scheduled_date - today).days,
                "assigned_to_type": "child"
            })

    return Response({"reminders": reminders})