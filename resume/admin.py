from django.contrib import admin
from .models import Resume, User

@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "email", "phone", "created_at"]
    search_fields = ["name", "email"]

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["id", "Name", "Email", "Phone", "is_premium", "daily_generations_left"]
    search_fields = ["Name", "Email"]