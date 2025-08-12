from rest_framework.authentication import TokenAuthentication
from authentication.models import Employee
from rest_framework.exceptions import AuthenticationFailed

class EmployeeTokenAuthentication(TokenAuthentication):
    def authenticate_credentials(self, key):
        from rest_framework.authtoken.models import Token
        try:
            token = Token.objects.select_related('user').get(key=key)
        except Token.DoesNotExist:
            raise AuthenticationFailed('Invalid token.')

        user = token.user
        try:
            employee = Employee.objects.get(user=user)
        except Employee.DoesNotExist:
            raise AuthenticationFailed('No employee associated with this user.')

        return employee, token
