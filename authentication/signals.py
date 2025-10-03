from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_currentuser.middleware import (get_current_authenticated_user, get_current_user)

from authentication.models import *

User = get_user_model()


def created_by_signals(sender, instance, created, **kwargs):
	if created:
		user = get_current_authenticated_user()
		if user is not None:
			sender.objects.filter(id=instance.id).update(created_by=user)


def updated_by_signals(sender, instance, created, **kwargs):
	if not created:
		user = get_current_authenticated_user()
		if user is not None:
			sender.objects.filter(id=instance.id).update(updated_by=user)


@receiver(post_save, sender=User)
def create_user_subscription(sender, instance, created, **kwargs):
    """
    Automatically create a subscription and start trial when a new user is created.
    """
    if created:  # Only for newly created users
        subscription = Subscription.objects.create(user=instance)
        subscription.start_trial()  # Start the 7-day trial immediately

        
# Branch signals
post_save.connect(created_by_signals, sender=Branch)
post_save.connect(updated_by_signals, sender=Branch)

# City signals
post_save.connect(created_by_signals, sender=City)
post_save.connect(updated_by_signals, sender=City)

# Country signals
post_save.connect(created_by_signals, sender=Country)
post_save.connect(updated_by_signals, sender=Country)

# Employee signals
post_save.connect(created_by_signals, sender=Employee)
post_save.connect(updated_by_signals, sender=Employee)

# Permission signals
post_save.connect(created_by_signals, sender=Permission)
post_save.connect(updated_by_signals, sender=Permission)

# Role signals
post_save.connect(created_by_signals, sender=Role)
post_save.connect(updated_by_signals, sender=Role)

# Designation signals
post_save.connect(created_by_signals, sender=Designation)
post_save.connect(updated_by_signals, sender=Designation)

# User signals
post_save.connect(created_by_signals, sender=User)
post_save.connect(updated_by_signals, sender=User)

# LoginHistory signals
post_save.connect(created_by_signals, sender=LoginHistory)
post_save.connect(updated_by_signals, sender=LoginHistory)


