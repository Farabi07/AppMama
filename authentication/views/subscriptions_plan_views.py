from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from authentication.models import SubscriptionPlan

@api_view(['GET'])
@permission_classes([AllowAny])
def list_subscription_plans(request):
    plans = SubscriptionPlan.objects.all()
    data = [
        {
            "id": plan.id,
            "name": plan.name,
            "plan_id": plan.plan_id,
            "duration_days": plan.duration_days,
            "price": str(plan.price),
        }
        for plan in plans
    ]
    return Response(data)