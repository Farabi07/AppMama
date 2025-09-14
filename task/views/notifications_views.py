from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from notification.models import Notification
from authentication.models import Child, Partner
from django.http import JsonResponse

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
