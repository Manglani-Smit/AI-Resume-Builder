from django.db import models

# Create your models here.
class Resume(models.Model):

    name = models.CharField(max_length=100)

    email = models.EmailField()

    phone = models.CharField(max_length=15)

    skills = models.TextField()

    education = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    summary = models.TextField(blank=True)

    template_id = models.IntegerField(default=1)

    projects = models.TextField(blank=True)

    experience = models.TextField(blank=True)

    certifications = models.TextField(blank=True)

    achievements = models.TextField(blank=True)

    objective = models.TextField(blank=True)

    def __str__(self):
        return self.name

class User(models.Model):
    Name = models.CharField(max_length=100)
    Email = models.EmailField()
    Phone = models.CharField(max_length=15)
    Password = models.CharField(max_length=100)

    def __str__(self):
        return self.Name

