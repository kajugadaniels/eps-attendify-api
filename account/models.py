import os
import random
from django.db import models
from account.managers import *
from django.utils import timezone
from django.utils.text import slugify
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

class User(AbstractBaseUser, PermissionsMixin):
    STATUS_CHOICE = [
        ('Admin', 'Admin'),
        ('User', 'User'),
    ]

    name = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    phone_number = models.CharField(unique=True, max_length=20, null=True, blank=True)
    role = models.CharField(choices=STATUS_CHOICE, max_length=50, null=True, blank=True)
    password = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name', 'phone_number']

    def __str__(self):
        return f"{self.name}"