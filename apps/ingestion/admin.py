from django.contrib import admin
from .models import DataSource, ConnectorConfig, ImportRun

@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'source_type', 'health_status', 'is_active', 'last_sync_at')
    list_filter = ('source_type', 'health_status', 'is_active')
    search_fields = ('name',)

@admin.register(ConnectorConfig)
class ConnectorConfigAdmin(admin.ModelAdmin):
    list_display = ('data_source', 'api_endpoint', 'updated_at')
    search_fields = ('data_source__name', 'api_endpoint')

@admin.register(ImportRun)
class ImportRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'file_name', 'data_source', 'total_rows', 'imported_rows', 'duplicate_rows', 'status', 'created_at')
    list_filter = ('status', 'data_source')
    search_fields = ('file_name',)
