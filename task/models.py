from django.db import models
from django.conf import settings
from django.utils import timezone


class TaskCategory(models.Model):
    """Task categories for organization"""
    CATEGORY_TYPES = [
        ('personal', 'Personal'),
        ('family', 'Family'), 
        ('business', 'Business'),
        ('health', 'Health'),
        ('education', 'Education'),
        ('household', 'Household'),
        ('recipe', 'Recipe'),
        ('other', 'Other')
    ]
    
    name = models.CharField(max_length=100)
    category_type = models.CharField(max_length=20, choices=CATEGORY_TYPES)
    color_code = models.CharField(max_length=7, default='#3498db')  # Hex color
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='task_categories')
    is_default = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.name} ({self.get_category_type_display()})"


class Task(models.Model):
    """Main task model based on AI response structure"""
    PRIORITY_CHOICES = [
        ('low', 'Low Priority'),
        ('medium', 'Medium Priority'), 
        ('high', 'High Priority'),
        ('urgent', 'Urgent')
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('overdue', 'Overdue')
    ]
    
    ASSIGNED_TO_CHOICES = [
        ('self', 'Self'),
        ('partner', 'Partner'),
        ('child', 'Child'),
        ('family', 'Whole Family')
    ]
    
    # Core task fields matching AI response
    task_name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    
    # Time and date fields
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField(blank=True, null=True)
    duration_minutes = models.PositiveIntegerField(blank=True, null=True)
    
    # Assignment and categorization
    assigned_to_type = models.CharField(max_length=20, choices=ASSIGNED_TO_CHOICES)
    assigned_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True, related_name='assigned_tasks')
    task_category = models.ForeignKey('TaskCategory', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Priority and status
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Family and ownership
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_tasks')
    
    # Partner and Child relationships - make sure Partner and Child models are correctly defined and imported
    assigned_partner = models.ForeignKey('authentication.Partner', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks')
    assigned_child = models.ForeignKey('authentication.Child', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks')
    
    # AI and metadata
    generated_by_ai = models.BooleanField(default=False)
    ai_session_id = models.CharField(max_length=100, blank=True, null=True)
    raw_ai_response = models.JSONField(blank=True, null=True)  # Store original AI JSON
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    # Recurring task support
    is_recurring = models.BooleanField(default=False)
    recurrence_pattern = models.CharField(max_length=50, blank=True, null=True)  # daily, weekly, monthly
    
    class Meta:
        ordering = ['scheduled_date', 'scheduled_time', 'priority']
        indexes = [
            models.Index(fields=['scheduled_date', 'created_by']),
            models.Index(fields=['assigned_user', 'status']),
            models.Index(fields=['priority', 'scheduled_date']),
        ]
    
    def __str__(self):
        return f"{self.task_name} - {self.get_assigned_to_type_display()}"
    
    @property
    def is_overdue(self):
        """Check if task is overdue"""
        if self.status == 'completed':
            return False
        
        now = timezone.now()
        scheduled_datetime = timezone.datetime.combine(self.scheduled_date, self.scheduled_time or timezone.datetime.min.time())
        scheduled_datetime = timezone.make_aware(scheduled_datetime)
        
        return now > scheduled_datetime
    
    def mark_completed(self):
        """Mark task as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()


class TaskBatch(models.Model):
    """Group of tasks created together from AI response"""
    batch_id = models.CharField(max_length=100, unique=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    ai_prompt = models.TextField()  # Original user input
    total_tasks = models.PositiveIntegerField()
    generated_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete= models.SET_NULL, related_name="+", null=True, blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete= models.SET_NULL, related_name="+", null=True, blank=True)
    
    
    def __str__(self):
        return f"Batch {self.batch_id} - {self.total_tasks} tasks"


class TaskComment(models.Model):
    """Comments and notes on tasks"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']


class TaskAttachment(models.Model):
    """File attachments for tasks"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='task_attachments/')
    filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete= models.SET_NULL, related_name="+", null=True, blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete= models.SET_NULL, related_name="+", null=True, blank=True)
    
# Recipe-specific model for meal planning tasks
class Recipe(models.Model):
    """Recipe model for meal planning tasks"""
    MEAL_TYPES = [
        ('breakfast', 'Breakfast'),
        ('brunch', 'Brunch'),
        ('lunch', 'Lunch'),
        ('dinner', 'Dinner'),
        ('snack', 'Snack')
    ]
    
    name = models.CharField(max_length=200)
    meal_type = models.CharField(max_length=20, choices=MEAL_TYPES)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='recipes')
    
    # Ingredients and instructions
    items_available = models.TextField()
    items_needed = models.TextField(blank=True, null=True)
    instructions = models.TextField()
    cooking_time_minutes = models.PositiveIntegerField(blank=True, null=True)
    servings = models.PositiveIntegerField(default=1)
    
    # AI generated metadata
    ai_generated = models.BooleanField(default=False)
    kid_friendly_tip = models.TextField(blank=True, null=True)
    serving_suggestion = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete= models.SET_NULL, related_name="+", null=True, blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete= models.SET_NULL, related_name="+", null=True, blank=True)
    
    
    def __str__(self):
        return f"{self.name} - {self.get_meal_type_display()}"

class Receipt(models.Model):
    # Basic information from the receipt
    image = models.ImageField(upload_to='receipts/')
    extracted_text = models.TextField(blank=True, null=True)
    extracted_data = models.JSONField(blank=True, null=True)

    # Detailed receipt information
    date = models.CharField(max_length=10, blank=True, null=True)  # e.g., 17-07-2025
    time = models.CharField(max_length=5, blank=True, null=True)   # e.g., 02:06
    shop_name = models.CharField(max_length=255, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    payment_method = models.CharField(max_length=100, blank=True, null=True)

    # For storing the items purchased
    items = models.JSONField(blank=True, null=True)  # List of dictionaries containing item info
    services = models.JSONField(blank=True, null=True)  # List of dictionaries containing services (if any)

    # Receipt financials
    vat_percentage = models.FloatField(blank=True, null=True)
    vat_amount = models.FloatField(blank=True, null=True)
    subtotal = models.FloatField(blank=True, null=True)
    tax = models.FloatField(blank=True, null=True)  # Total tax amount
    discount = models.FloatField(blank=True, null=True)
    total_cost = models.FloatField(blank=True, null=True)

    # Timestamps for when the receipt was uploaded and processed
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete= models.SET_NULL, related_name="+", null=True, blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete= models.SET_NULL, related_name="+", null=True, blank=True)
    
    def __str__(self):
        return f"Receipt {self.id} - {self.shop_name} - {self.date}"

    def save(self, *args, **kwargs):
        if self.extracted_data:
            # Automatically set the processed_at field when the receipt is processed
            self.processed_at = self.processed_at or models.DateTimeField(auto_now_add=True).default
        super().save(*args, **kwargs)