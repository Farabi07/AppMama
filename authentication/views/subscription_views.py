import stripe
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.csrf import csrf_exempt
from authentication.models import Subscription, SubscriptionPlan
from django.conf import settings
import json
from django.http import JsonResponse
from django.contrib.auth import get_user_model
# Use Stripe secret key from settings
stripe.api_key = settings.STRIPE_SECRET_KEY

# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def create_subscription(request):
#     plan_id = request.data.get('plan_id')  # Stripe Price ID
#     user = request.user

#     # Get or create the subscription for the user
#     subscription, created = Subscription.objects.get_or_create(user=user)

#     # Get the plan from your DB
#     plan = SubscriptionPlan.objects.filter(plan_id=plan_id).first()
#     if not plan:
#         return Response({"error": "Invalid plan."}, status=400)

#     try:
#         # Create a Stripe Checkout Session for subscription
#         checkout_session = stripe.checkout.Session.create(
#             payment_method_types=['card'],
#             mode='subscription',
#             line_items=[{
#                 'price': plan.plan_id,  # Stripe Price ID
#                 'quantity': 1,
#             }],
#             customer_email=user.email,
#             success_url='https://your-frontend.com/success?session_id={CHECKOUT_SESSION_ID}',
#             cancel_url='https://your-frontend.com/cancel',
#         )
#         # Optionally, store the plan on the user's subscription for later use
#         subscription.plan = plan
#         subscription.save(update_fields=["plan"])
#         return Response({"checkout_url": checkout_session.url})
#     except Exception as e:
#         return Response({"error": str(e)}, status=400)
stripe.api_key = settings.STRIPE_SECRET_KEY
import stripe
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt



@csrf_exempt
def create_payment_intent(request):
    try:
        data = json.loads(request.body)
        print("Received data:", data)
        plan_id = data.get('plan_id')
        user = request.user

        # Look up the plan
        plan = SubscriptionPlan.objects.filter(plan_id=plan_id).first()
        if not plan:
            return JsonResponse({'error': 'Invalid plan.'}, status=400)

        # Create PaymentIntent with plan price and metadata
        payment_intent = stripe.PaymentIntent.create(
            amount=int(plan.price * 100),  # Stripe expects cents
            currency='usd',
            metadata={
                'user_id': str(user.id),
                'plan_id': plan_id
            }
        )

        return JsonResponse({
            'client_secret': payment_intent.client_secret
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_stripe_customer(request):
    user = request.user
    try:
        # Create a new Stripe customer using the user's email
        customer = stripe.Customer.create(email=user.email)

        # Respond with the customer ID (useful for later attachment of payment methods or subscription creation)
        return Response({"customer_id": customer.id}, status=200)
    except Exception as e:
        return Response({"error": str(e)}, status=400)
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def attach_payment_method(request):
    user = request.user
    payment_method_id = request.data.get('payment_method_id')  # Get the payment method ID from the request
    customer_id = request.data.get('customer_id')  # Get the customer ID from the request

    try:
        # Attach the payment method to the customer
        stripe.PaymentMethod.attach(payment_method_id, customer=customer_id)

        # Set the attached payment method as the default for the customer
        stripe.Customer.modify(
            customer_id,
            invoice_settings={'default_payment_method': payment_method_id},
        )

        return Response({"message": "Payment method attached successfully."}, status=200)
    except Exception as e:
        return Response({"error": str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_payment_method(request):
    card_data = request.data.get('card_data')  # Card data is passed as a parameter (e.g., number, exp_month, exp_year, cvc)
    try:
        # Create a payment method using Stripe's API
        payment_method = stripe.PaymentMethod.create(
            type="card",
            card=card_data
        )
        return Response({"payment_method_id": payment_method.id}, status=200)
    except Exception as e:
        return Response({"error": str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_subscription(request):
    user = request.user
    plan_id = request.data.get('plan_id')  # Stripe Price ID of the plan
    customer_id = request.data.get('customer_id')  # The customer ID returned earlier
    payment_method_id = request.data.get('payment_method_id')  # The payment method ID attached to the customer

    try:
        # Create the subscription using the provided details
        subscription = stripe.Subscription.create(
            customer=customer_id,
            items=[{"price": plan_id}],  # Stripe Price ID (Plan ID)
            default_payment_method=payment_method_id  # Use the attached payment method
        )

        return Response({"subscription_id": subscription.id}, status=200)
    except Exception as e:
        return Response({"error": str(e)}, status=400)

@csrf_exempt
def stripe_webhook(request):
    from django.utils import timezone
    from datetime import timedelta

    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_ENDPOINT_SECRET
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        print("Stripe event received:", event['type'])

        if event['type'] == 'payment_intent.succeeded':
            intent = event['data']['object']
            print("PaymentIntent metadata:", intent.get('metadata'))
            user_id = intent['metadata'].get('user_id')
            plan_id = intent['metadata'].get('plan_id')
            payment_intent_id = intent['id']
            amount = intent.get('amount_received', 0) / 100.0

            print("user_id:", user_id, "plan_id:", plan_id, "payment_intent_id:", payment_intent_id, "amount:", amount)

            from authentication.models import Subscription, SubscriptionPlan
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.filter(id=user_id).first()
            plan = SubscriptionPlan.objects.filter(plan_id=plan_id).first()
            print("User:", user)
            print("Plan:", plan)
            if user and plan:
                subscription, _ = Subscription.objects.get_or_create(user=user)
                subscription.plan = plan
                subscription.is_active = True
                subscription.started_at = timezone.now()
                subscription.expires_at = timezone.now() + timedelta(days=plan.duration_days)
                subscription.payment_method_token = payment_intent_id
                subscription.save(update_fields=["plan", "is_active", "started_at", "expires_at", "payment_method_token"])
                print("Subscription updated!")
            else:
                print("User or plan not found! user_id:", user_id, "plan_id:", plan_id)
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        print("Webhook error:", str(e))
        return JsonResponse({'error': str(e)}, status=400)
    
from datetime import datetime
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from authentication.models import Subscription
import logging

# Map product_id to subscription duration in days
PRODUCT_DURATION_MAP = {
    'family_mode_monthly': 30,
    'family_mode_yearly': 365,
    'boss_mode_monthly': 30,
    'boss_mode_yearly': 365,
}

# Logging setup for debugging
logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_subscription(request):
    data = request.data
    user = request.user

    logger.info(f"Received data: {data}")

    product_id = data.get('product_id')
    duration_days = PRODUCT_DURATION_MAP.get(product_id)
    if not duration_days:
        return Response({'error': 'Invalid product_id.'}, status=400)

    # Get price from frontend (optional)
    price = data.get('price')  # <-- Accept price from frontend

    started_at = timezone.now()
    expires_at = started_at + timezone.timedelta(days=duration_days)

    subscription, _ = Subscription.objects.get_or_create(user=user)
    subscription.is_active = True
    subscription.started_at = started_at
    subscription.expires_at = expires_at
    subscription.product_id = product_id
    subscription.platform = data.get('platform')
    subscription.purchase_token = data.get('purchase_token')
    subscription.transaction_id = data.get('transaction_id')
    subscription.original_transaction_id = data.get('original_transaction_id')
    if price is not None:
        subscription.price = price  # <-- Save price if your model has this field

    purchase_date_str = data.get('purchase_date')
    if purchase_date_str:
        try:
            normalized_purchase_date = purchase_date_str.replace('Z', '+00:00')
            subscription.purchase_date = datetime.fromisoformat(normalized_purchase_date)
        except ValueError as e:
            logger.error(f"Error parsing purchase_date: {purchase_date_str}. Error: {e}")
            return Response({'error': 'Invalid purchase_date format.'}, status=400)

    subscription.status_is = 'active subscription'
    subscription.save()

    return Response({'success': True, 'message': 'Subscription activated.'})
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def subscription_status(request):
    user = request.user
    try:
        subscription = Subscription.objects.get(user=user)
        
        # Sync status to ensure it's up to date
        subscription.sync_status()
        
        return Response({
            "status": subscription.status_is,
            "expires_at": subscription.expires_at,
        })
        
    except Subscription.DoesNotExist:
        # This should rarely happen if signal is working properly
        # But as a fallback, create subscription and start trial
        subscription = Subscription.objects.create(user=user)
        subscription.start_trial()
        
        return Response({
            "status": subscription.status_is,
            "expires_at": subscription.expires_at,
        })
    
@api_view(['GET'])
def all_users_subscription_status(request):
    User = get_user_model()
    all_users = User.objects.all()
    users_list = []
    subscriber_count = 0
    non_subscriber_count = 0

    for user in all_users:
        try:
            subscription = Subscription.objects.get(user=user)
            if subscription.is_subscription_active():
                status = "subscriber"
                subscriber_count += 1
            else:
                status = "non-subscriber"
                non_subscriber_count += 1
        except Subscription.DoesNotExist:
            status = "non-subscriber"
            non_subscriber_count += 1

        # Get the absolute image URL if image exists
        if user.image:
            image_url = request.build_absolute_uri(user.image.url)
        else:
            image_url = None

        users_list.append({
            "id": user.id,
            "email": user.email,
            "full_name": getattr(user, "full_name", ""),
            "status": status,
            "image": image_url,
        })

    result = {
        "users": users_list,
        "subscriber_count": subscriber_count,
        "non_subscriber_count": non_subscriber_count,
        "total_users": all_users.count()
    }
    return Response(result)