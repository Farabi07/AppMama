from task.models import *
from django_filters import rest_framework as filters
class TaskFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr='icontains')

    class Meta:
        model = Task
        fields = ['name', ]