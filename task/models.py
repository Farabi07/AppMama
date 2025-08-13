from django.db import models
from authentication.models import User
# Task Model
class Task(models.Model):
    PERSONAL = 'personal'
    BUSINESS = 'business'
    FAMILY = 'family'

    CATEGORY_CHOICES = [
        (PERSONAL, 'Personal'),
        (BUSINESS, 'Business'),
        (FAMILY, 'Family'),
    ]

    title = models.CharField(max_length=255,blank=True,null=True)
    description = models.TextField(blank=True,null=True)
    due_date = models.DateTimeField(blank=True,null=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default=PERSONAL)
    priority = models.IntegerField(default=3,blank=True,null=True)  # Lower number = higher priority
    user = models.ForeignKey(User, on_delete=models.CASCADE,blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

# # Mood Tracking Model
# class Mood(models.Model):
#     MOOD_CHOICES = [
#         ('happy', 'Happy'),
#         ('stressed', 'Stressed'),
#         ('calm', 'Calm'),
#         ('sad', 'Sad'),
#     ]

#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     mood = models.CharField(max_length=10, choices=MOOD_CHOICES)
#     date = models.DateField(auto_now_add=True)

#     def __str__(self):
#         return f'{self.user.username} - {self.mood}'
