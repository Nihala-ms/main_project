from django.contrib import admin
from django.core.mail import send_mail
from .models import Users, PatientsProfiles, DoctorsProfiles,Appointments,DoctorAdditionalInfo


@admin.register(DoctorsProfiles)
class DoctorsProfilesAdmin(admin.ModelAdmin):
    list_display = ('user', 'specialization', 'experience_years', 'approved')
    list_filter = ('approved',)
    actions = ['approve_doctors']

    def approve_doctors(self, request, queryset):
        unapproved_doctors = queryset.filter(approved=False)
        for doctor in unapproved_doctors:
            doctor.approved = True
            doctor.save()

            # Send approval email to doctor
            send_mail(
                'Approval Notification',
                f'Dear Dr. {doctor.user.first_name},\n\nYour account has been approved. You can now log in to our platform.\n\nThank you,\nAdmin Team',
                'nihalabinthsalih786@gmail.com.com',  # Replace with your email
                [doctor.email],
                fail_silently=False,
            )

        self.message_user(request, f'{len(unapproved_doctors)} doctor(s) approved and notified via email.')
    approve_doctors.short_description = "Approve selected doctors"

@admin.register(Users)
class UsersAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_patient', 'is_doctor', 'is_admin')

@admin.register(PatientsProfiles)
class PatientsProfilesAdmin(admin.ModelAdmin):
    list_display = ('user', 'email', 'phonenumber', 'gender')
    
admin.site.register(Appointments)
admin.site.register(DoctorAdditionalInfo)



