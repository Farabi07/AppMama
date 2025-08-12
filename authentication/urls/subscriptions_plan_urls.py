from authentication.views import subscriptions_plan_views as views
from django.urls import path
urlpatterns = [
    path('api/v1/subscription/plans/', views.list_subscription_plans, name='list_subscription_plans'),

]