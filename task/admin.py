from django.contrib import admin
from django.contrib.auth.models import Group
from .models import *

# Register TaskCategory model
@admin.register(TaskCategory)
class TaskCategoryAdmin(admin.ModelAdmin):
    list_display = [field.name for field in TaskCategory._meta.fields]

# Register Task model
@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Task._meta.fields]

# Register TaskBatch model
@admin.register(TaskBatch)
class TaskBatchAdmin(admin.ModelAdmin):
    list_display = [field.name for field in TaskBatch._meta.fields]

# Register TaskComment model
@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = [field.name for field in TaskComment._meta.fields]

# Register TaskAttachment model
@admin.register(TaskAttachment)
class TaskAttachmentAdmin(admin.ModelAdmin):
    list_display = [field.name for field in TaskAttachment._meta.fields]

# Register Recipe model
@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Recipe._meta.fields]
    
@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Receipt._meta.fields]