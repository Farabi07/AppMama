from django.contrib import admin
from django.contrib.auth.models import Group

from .models import *

@admin.register(Designation)
class DesignationAdmin(admin.ModelAdmin):
	list_display = [field.name for field in Designation._meta.fields]


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
	list_display = [field.name for field in User._meta.fields]


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
	list_display = [field.name for field in Employee._meta.fields]

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
	list_display = [field.name for field in Role._meta.fields]


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
	list_display = [field.name for field in Permission._meta.fields]

@admin.register(City)
class CityAdmin(admin.ModelAdmin):
	list_display = [field.name for field in City._meta.fields]


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
	list_display = [field.name for field in Country._meta.fields]

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
	list_display = [field.name for field in Branch._meta.fields]


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
	list_display = [field.name for field in LoginHistory._meta.fields]

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
	list_display = [field.name for field in Subscription._meta.fields]
@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
	list_display = [field.name for field in SubscriptionPlan._meta.fields]
@admin.register(ScanUsage)
class ScanUsageAdmin(admin.ModelAdmin):
	list_display = [field.name for field in ScanUsage._meta.fields]
admin.site.unregister(Group)
@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
	list_display = [field.name for field in Partner._meta.fields]
@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
	list_display = [field.name for field in Child._meta.fields]