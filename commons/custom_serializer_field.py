
from rest_framework import serializers, status
from rest_framework.response import Response
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.serializers import ValidationError

class ReadWriteSerializerMethodField(serializers.Field):
	def __init__(self, method_name=None, model=None, **kwargs):
		self.method_name = method_name
		self.model = model
		kwargs['source'] = '*'
		super().__init__(**kwargs)
		

	def bind(self, field_name, parent):
		# The method name defaults to `get_{field_name}`.
		if self.method_name is None:
			self.method_name = 'get_{field_name}'.format(field_name=field_name)
		super().bind(field_name, parent)

	
	def to_internal_value(self, value):
		# print(f"to_internal_value called {self.model.__name__} ----->" , value, type(value))

		if self.model and (isinstance(value, int) or value.isdigit()):
			try:
				data = self.model.objects.get(pk=value)
				return {self.field_name: data}
			except ObjectDoesNotExist:
				raise ValidationError(f"{self.model.__name__} pk - {value} doesn't exists")
		elif value is None:
			return {self.field_name: value}
		else:
			raise ValidationError(f"The value you enter is not a interger or model parameter is missing on {type(self).__name__} in {type(self.parent).__name__}")


	def to_representation(self, value):
		method = getattr(self.parent, self.method_name)
		return method(value)
