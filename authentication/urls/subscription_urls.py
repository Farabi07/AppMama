from authentication.views import subscription_views as views
from django.urls import path

	

urlpatterns = [
    # API endpoint for creating a subscription
    path('api/v1/subscription/create/', views.create_subscription, name='create_subscription'),
    
    # API endpoint for handling Stripe webhooks
    path('api/v1/subscription/stripe-webhook/', views.stripe_webhook, name='stripe_webhook'),
    
    # API endpoint for creating a Stripe customer
    path('api/v1/subscription/create-stripe-customer/', views.create_stripe_customer, name='create_stripe_customer'),
    
    # API endpoint for attaching a payment method to a Stripe customer
    path('api/v1/subscription/attach-payment-method/', views.attach_payment_method, name='attach_payment_method'),
    path('api/v1/create-payment-intent/', views.create_payment_intent, name='create_payment_intent'),
    # API endpoint for creating a payment method
    path('api/v1/subscription/create-payment-method/', views.create_payment_method, name='create_payment_method'),

    path('verify-inapp-purchase/', views.save_subscription, name='verify_inapp_purchase'),
    path('api/v1/subscription/activate/', views.subscription_status, name='subscription_status'),

    path('all-users-subscription-status/', views.all_users_subscription_status, name='all_users_subscription_status'),
]
   
