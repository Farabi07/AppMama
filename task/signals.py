# task/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Task
from notification.models import Notification
from authentication.models import Child, Partner
import logging

logger = logging.getLogger(__name__)  # Initialize logger

# @receiver(post_save, sender=Task)
# def create_notification_on_task_create(sender, instance, created, **kwargs):
#     if created:
#         task = instance  # The task that was just created
#         task_name = task.task_name
#         scheduled_date = task.scheduled_date
#         scheduled_time = task.scheduled_time
#         assigned_to_type = task.assigned_to_type.lower()  # Ensuring lowercase comparison
#         message = f"You have been assigned a task: {task_name} on {scheduled_date} at {scheduled_time}."
        
#         # Log that the signal is triggered
#         logger.info(f"Signal triggered for task: {task_name} with assigned type: {assigned_to_type}")

#         # If the task is assigned to a child
#         if assigned_to_type == 'child':
#             children = Child.objects.all()
#             for child in children:
#                 Notification.objects.create(user=child.user, task=task, message=message)
#                 logger.info(f"Notification created for child: {child.user}")

#         # If the task is assigned to a partner
#         elif assigned_to_type == 'partner':
#             partners = Partner.objects.all()
#             for partner in partners:
#                 Notification.objects.create(user=partner.user, task=task, message=message)
#                 logger.info(f"Notification created for partner: {partner.user}")

#         # If the task is assigned to self (admin)
#         elif assigned_to_type == 'self':
#             Notification.objects.create(user=task.created_by, task=task, message=message)
#             logger.info(f"Notification created for admin: {task.created_by}")


@receiver(post_save, sender=Task)
def create_notification_on_task_create(sender, instance, created, **kwargs):
    if created:
        task = instance  # The task that was just created
        task_name = task.task_name
        scheduled_date = task.scheduled_date
        scheduled_time = task.scheduled_time
        assigned_to_type = task.assigned_to_type.lower()  # Ensuring lowercase comparison
        message = f"You have been assigned a task: {task_name} on {scheduled_date} at {scheduled_time}."
        
        # Log that the signal is triggered
        logger.info(f"Signal triggered for task: {task_name} with assigned type: {assigned_to_type}")

        # If the task is assigned to child (send notification to all children)
        if assigned_to_type == 'child':
            children = Child.objects.all()  # Get all children
            for child in children:
                Notification.objects.create(user=child.user, task=task, message=message)
                logger.info(f"Notification created for child: {child.user}")

        # If the task is assigned to partner (send notification to all partners)
        elif assigned_to_type == 'partner':
            partners = Partner.objects.all()  # Get all partners
            for partner in partners:
                Notification.objects.create(user=partner.user, task=task, message=message)
                logger.info(f"Notification created for partner: {partner.user}")

        # If the task is assigned to self (admin), create notification for the admin
        elif assigned_to_type == 'self':
            Notification.objects.create(user=task.created_by, task=task, message=message)
            logger.info(f"Notification created for admin: {task.created_by}")