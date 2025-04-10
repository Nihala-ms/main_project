from django.utils import timezone
from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils.crypto import get_random_string
from django.contrib.auth.models import User
from django.utils.timezone import now


class Users(AbstractUser):
    first_name = models.CharField(max_length=100, null=True, blank=True)
    is_admin = models.BooleanField('Is Admin', default=False)
    is_patient = models.BooleanField('Is Patient', default=False)
    is_doctor = models.BooleanField('Is Doctor', default=False)

    groups = models.ManyToManyField(
        Group,
        related_name='custom_user_groups',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='custom_user_permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    def __str__(self):
        return self.username

class DoctorsProfiles(models.Model):
    user = models.OneToOneField(Users, on_delete=models.CASCADE, related_name='doctorsprofile')
    email = models.EmailField(unique=True, max_length=50, null=False, default='default@example.com')
    specialization = models.CharField(max_length=255)
    experience_years = models.IntegerField()
    certificate = models.FileField(upload_to='certificates/')
    license_number = models.CharField(max_length=50,unique=True)
    hospital = models.CharField(max_length=200, default="Default Hospital")
    approved = models.BooleanField(default=False)  # Ensure this field is present
    available_days = models.CharField(max_length=100,help_text="Comma-separated list of available days, e.g., Monday, Wednesday, Friday")  # Comma-separated days
    available_time_start = models.TimeField(null=True)  # Start time for availability
    available_time_end = models.TimeField(null=True)     
    
    def __str__(self):
        return f"Dr. {self.user}"
    

class DoctorAdditionalInfo(models.Model):
    doctor = models.OneToOneField(DoctorsProfiles, on_delete=models.CASCADE, related_name='additional_info')
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    hospitals = models.CharField(max_length=200, default="Default Hospital")
    qualifications = models.TextField(blank=True, null=True)
    bio = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Additional Info for Dr. {self.doctor.user.username}"
    



class PatientsProfiles(models.Model):
    user = models.OneToOneField(Users, on_delete=models.CASCADE, related_name='patientsprofile')
    email = models.EmailField(unique=True, max_length=50, null=False)
    phonenumber = models.CharField(max_length=12,null=True)
    is_doctor = models.BooleanField(default=False)  # Add default value to the field
    gender = models.CharField(
        max_length=20,
        choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')],
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.user.first_name}"
class Appointments(models.Model):
    doctor = models.ForeignKey(DoctorsProfiles, on_delete=models.CASCADE)
    patient = models.ForeignKey(PatientsProfiles, on_delete=models.CASCADE)
    date = models.DateField()
    token_number = models.PositiveIntegerField(null=True, blank=True, default=1)
    time_slot = models.TimeField(default='09:00:00')  # Default time slot
    payment_status = models.CharField(
        max_length=10, 
        choices=[('Pending', 'Pending'), ('Completed', 'Completed')], 
        default='Pending')
    amount_paid = models.DecimalField(max_digits=8, decimal_places=2, default=200.00)  # Fixed amount
    video_link = models.URLField(blank=True, null=True, unique=True,max_length=225)  # Link to video conference
    prescription_text = models.TextField(blank=True, null=True)  # Text prescription
    prescription_file = models.FileField(upload_to='prescriptions/', blank=True, null=True) 
    is_video_link_sent = models.BooleanField(default=False)
    completed = models.BooleanField(default=False)
    completion_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Appointment with Dr. {self.doctor.user} on {self.date}"




