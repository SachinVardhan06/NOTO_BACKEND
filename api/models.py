from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.timezone import now, timedelta
from django.utils import timezone

# Custom User Manager
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


# Custom User Model
class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now, editable=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


# Subscription Model
class Subscription(models.Model):
    MEMBERSHIP_CHOICES = [
        ('Free', 'Free'),
        ('Basic', 'Basic'),
        ('Premium', 'Premium'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    membership_type = models.CharField(max_length=50, choices=MEMBERSHIP_CHOICES, default='Free')
    purchase_date = models.DateTimeField(default=now)
    start_date = models.DateTimeField(default=now)
    
    # Use a callable function for the default value of end_date
    def get_end_date():
        return timezone.now() + timedelta(days=30)

    end_date = models.DateTimeField(default=get_end_date)

    @property
    def time_left(self):
        remaining_time = self.end_date - timezone.now()
        days = remaining_time.days
        if days > 0:
            return f"{days} days left"
        else:
            return "Expired"

    def __str__(self):
        return f"{self.user.email} - {self.membership_type}"


