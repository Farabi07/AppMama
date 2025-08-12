from django.core.mail import send_mail

def send_employee_credentials(email, password):
    subject = "Your Employee Account Credentials"
    message = (
        f"Welcome!\n\n"
        f"Your account has been created.\n"
        f"Login Email: {email}\n"
        f"Password: {password}\n\n"
        f"Please log in and change your password after first login."
    )
    send_mail(
        subject,
        message,
        None,  # Uses DEFAULT_FROM_EMAIL
        [email],
        fail_silently=False,
    )