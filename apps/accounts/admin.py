from django.contrib import admin
from .models import StaffProfile

@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'employee_id', 'role', 'department', 'assigned_ward', 'phone_number')
    list_filter = ('role', 'department', 'assigned_ward__zone')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'employee_id')
