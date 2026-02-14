from django.contrib import admin
from .models import Appointment

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('identifier', 'title', 'date_time', 'user', 'notified_1h', 'notified_5min')
    list_filter = ('date_time', 'notified_1h', 'notified_5min', 'user')
    search_fields = ('title', 'identifier')
    readonly_fields = ('identifier', 'created_at', 'updated_at')
