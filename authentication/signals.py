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


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_subscription_and_start_trial(sender, instance, created, **kwargs):
    if created:
        # Create subscription with trial started now
        Subscription.objects.create(
            user=instance,
            trial_started_at=timezone.now(),
            trial_used=False,
            is_active=False
            
        )
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


