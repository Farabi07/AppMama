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
]
    # path('api/v1/subscription/activate/', views.activate_subscription, name='activate_subscription'),
    # path('api/v1/subscription/cancel/', views.cancel_subscription, name='cancel_subscription'),
    # path('api/v1/subscription/renew/', views.renew_subscription, name='renew_subscription'),
    # path('api/v1/subscription/upgrade/', views.upgrade_subscription, name='upgrade_subscription'),
    # path('api/v1/subscription/downgrade/', views.downgrade_subscription, name='downgrade_subscription'),
    # path('api/v1/subscription/get/', views.get_subscription, name='get_subscription'),
    # path('api/v1/subscription/get_all/', views.get_all_subscriptions, name='get_all_subscriptions'),
    # path('api/v1/subscription/get_active/', views.get_active_subscription, name='get_active_subscription'),
    # path('api/v1/subscription/get_inactive/', views.get_inactive_subscription, name='get_inactive_subscription'),
    # path('api/v1/subscription/get_trial/', views.get_trial_subscription, name='get_trial_subscription'),
    # path('api/v1/subscription/get_expired/', views.get_expired_subscription, name='get_expired_subscription'),
    # path('api/v1/subscription/get_by_user/<int:user_id>/', views.get_subscription_by_user, name='get_subscription_by_user'),

