from django.db import models
from django.utils import timezone


class User(models.Model):
    Name = models.CharField(max_length=100)
    Email = models.EmailField(unique=True)
    Phone = models.CharField(max_length=15)
    Password = models.CharField(max_length=100)

    # Premium & Daily Limit System
    is_premium = models.BooleanField(default=False)
    daily_generations_left = models.IntegerField(default=3)
    last_generation_date = models.DateField(default=timezone.now)

    def reset_daily_limit_if_needed(self):
        today = timezone.now().date()
        if self.last_generation_date < today:
            self.daily_generations_left = 3
            self.last_generation_date = today
            self.save()

    def can_generate(self):
        self.reset_daily_limit_if_needed()
        if self.is_premium:
            return True
        return self.daily_generations_left > 0

    def deduct_generation(self):
        if not self.is_premium and self.daily_generations_left > 0:
            self.daily_generations_left -= 1
            self.save()

    def __str__(self):
        return self.Name


class Resume(models.Model):
    # Har resume ko user se link kar diya
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resumes')
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    skills = models.TextField()
    education = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    summary = models.TextField(blank=True)
    template_id = models.IntegerField(default=1)

    # Dynamic Multiple Projects JSON format mein
    projects = models.JSONField(default=list, blank=True)
    experience = models.TextField(blank=True)
    certifications = models.TextField(blank=True)
    achievements = models.TextField(blank=True)
    objective = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} - {self.user.Name}"