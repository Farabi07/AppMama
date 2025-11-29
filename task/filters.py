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
        fields = ['task_name', ]

class RecipeFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="title", lookup_expr='icontains')

    class Meta:
        model = Recipe
        fields = ['name', ]

class ClientFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr='icontains')

    class Meta:
        model = Client
        fields = ['name', ]

class ReceiptFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="title", lookup_expr='icontains')

    class Meta:
        model = Receipt
        fields = ['name', ]
class PeptalkFilter(filters.FilterSet):
    title = filters.CharFilter(field_name="title", lookup_expr='icontains')

    class Meta:
        model = PeptalkData
        fields = ['title', ]

class PantryFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr='icontains')

    class Meta:
        model = Pantry
        fields = ['name', ]