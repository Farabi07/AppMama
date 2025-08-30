from task.models import *
from django_filters import rest_framework as filters
class TaskCategoryFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr='icontains')

    class Meta:
        model = TaskCategory
        fields = ['name', ]

class TaskFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr='icontains')

    class Meta:
        model = Task
        fields = ['name', ]

class RecipeFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="title", lookup_expr='icontains')

    class Meta:
        model = Recipe
        fields = ['name', ]