from django.contrib import admin
from .models import Department, CivicCategory, CivicLocation

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'head_title', 'head_email', 'is_active')
    search_fields = ('name', 'code', 'head_title')
    list_filter = ('is_active',)
    prepopulated_fields = {'code': ('name',)}

@admin.register(CivicCategory)
class CivicCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'department', 'is_active')
    search_fields = ('name', 'code', 'keywords_en', 'keywords_gu', 'keywords_hi')
    list_filter = ('department', 'is_active')
    prepopulated_fields = {'code': ('name',)}

@admin.register(CivicLocation)
class CivicLocationAdmin(admin.ModelAdmin):
    list_display = ('ward_number', 'ward_name', 'zone', 'known_landmarks')
    search_fields = ('ward_name', 'known_landmarks')
    list_filter = ('zone',)
