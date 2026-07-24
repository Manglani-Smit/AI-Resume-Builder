from django.contrib import admin
from .models import *
# Register your models here.
class ResumeAdmin(admin.ModelAdmin):
    list_display = ["name","email","phone","skills","education","created_at","summary","template_id","projects","experience","certifications","achievements","objective"]

admin.site.register(Resume, ResumeAdmin)

class UserAdmin(admin.ModelAdmin):
    list_display = ["Name","Email","Phone","Password"]

admin.site.register(User, UserAdmin)