from django.db import models

class Department(models.Model):
    name = models.CharField(max_length=100, null=True, blank=True)
    day_salary = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.name