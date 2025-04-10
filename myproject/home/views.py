from email.message import EmailMessage
from time import timezone
from django.utils import timezone
from django.contrib.auth.models import User
from django.http import FileResponse, Http404, JsonResponse
from django.utils.timezone import now
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db import IntegrityError
from django.core.mail import send_mail
from .models import Users,Appointments,DoctorsProfiles,PatientsProfiles,DoctorAdditionalInfo
from pharmacy.models import Medicine,Brand,Products,Orders,OrderItem
from django.conf import settings
import re
from django.db import transaction
import pdfkit  # Install using `pip install pdfkit`
import os
from django.urls import reverse
from datetime import date
from datetime import datetime, timedelta, time
from django.contrib.auth.hashers import check_password  # Import check_password
import razorpay

def signup(request):
    if request.method == 'POST':
        user_type = request.POST.get('user_type')
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['userpassword']

        try:
            if Users.objects.filter(email=email).exists():
                messages.error(request, 'A user with this email already exists.')
                return redirect('signup')
            email_regex = r'^[a-zA-Z0-9._%+-]+@gmail+.com$'
            if not re.match(email_regex, email):
                messages.error(request, "Invalid email format.")
                return redirect('signup') 

            user = Users.objects.create_user(username=username, email=email, password=password)
            user.is_patient = (user_type == 'patient')
            user.is_doctor = (user_type == 'doctor')
            user.save()
            request.session['user_id'] = user.id  # Set session for newly registered user


            if user.is_patient:
                phonenumber = request.POST['phonenumber']
                gender = request.POST['gender']
                PatientsProfiles.objects.create(user=user, email=email, phonenumber=phonenumber, gender=gender)
                messages.success(request, 'Patient registered successfully!')
                return redirect(signin)
            elif user.is_doctor:
                specialization = request.POST['doctor_specialization']
                experience_years = request.POST['experience_years']
                license_number = request.POST['license_number']
                hospital = request.POST['hospital']
                available_days =request.POST.get('available_days')  # Convert list to comma-separated string
                available_time_start = request.POST['available_time_start']
                available_time_end = request.POST['available_time_end'] # Make sure to get the file correctly
                certificate = request.FILES.get('certificate')

                if not certificate:
                    messages.error(request, 'Please upload the certificate.')
                    return redirect('signup')
                
                DoctorsProfiles.objects.create(
                    user=user,
                    email=email,
                    specialization=specialization,
                    experience_years=experience_years,
                    certificate=certificate,  # Store the file
                    license_number=license_number,
                    hospital=hospital,
                    available_days=available_days,
                    available_time_start=available_time_start,
                    available_time_end=available_time_end,
                )
                messages.success(request, 'Doctor registration submitted successfully!')

            # Automatically log in the user
            login(request, user)
            return redirect('patient_dashboard' if user.is_patient else 'registration_success')

        except IntegrityError:
            messages.error(request, 'Registration failed. Please try again.')
            return redirect('signup')

    return render(request, 'signup.html')

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.hashers import check_password
from .models import Users

def signin(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "").strip()

        # Validate input
        if not email or not password:
            messages.error(request, "Email and password are required.")
            return redirect('signin')

        # Attempt to get user
        user = Users.objects.filter(email=email).first()
        if not user or not check_password(password, user.password):
            messages.error(request, "Invalid email or password.")
            return redirect('signin')

        # Check if account is active
        if not user.is_active:
            messages.error(request, "Your account is inactive. Please contact support.")
            return redirect('signin')

        # Log the user in
        login(request, user)
        request.session['user_id'] = user.id
        request.session['user_role'] = 'admin' if user.is_admin else 'doctor' if user.is_doctor else 'patient'

        # Redirect after login
        next_url = request.GET.get('next')
        if next_url:
            return redirect(next_url)

        # Redirect based on user roles
        if user.is_admin:
            return redirect('admin_dashboard')
        elif user.is_doctor:
            if hasattr(user, 'doctorsprofile') and not user.doctorsprofile.approved:
                messages.error(request, "Your account is pending admin approval.")
                return redirect('signin')
            return redirect('doctor_dashboard')
        elif user.is_patient:
            return redirect('patient_dashboard')

        # Fallback for invalid user role
        messages.error(request, "Invalid user role.")
        return redirect('signin')

    # Render the sign-in form for GET requests
    return render(request, 'signin.html')


#def signin(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "").strip()

        try:
            # Fetch user by email
            user = Users.objects.get(email=email)
        except Users.DoesNotExist:
            messages.error(request, "Invalid email or password.")
            return redirect('signin')

        # Verify the password
        if check_password(password, user.password):
            request.session['user_id'] = user.id  # or any session setup for custom models

            if not user.is_active:
                messages.error(request, "Your account is inactive. Please contact support.")
                return redirect('signin')

            # Log the user in
            login(request, user)

            # Handle the 'next' parameter for redirecting after login
            next_url = request.GET.get('next', None)
            if next_url:
                return redirect(next_url)

            # Redirect based on user roles
            if user.is_admin:
                return redirect('admin_dashboard')
            elif user.is_doctor:
                # Check if doctor approval is required
                if hasattr(user, 'doctorsprofile') and not user.doctorsprofile.approved:
                    messages.error(request, "Your account is pending admin approval.")
                    return redirect('signin')
                return redirect('doctor_dashboard')
            elif user.is_patient:
                return redirect('patient_dashboard')
            else:
                messages.error(request, "Invalid user role.")
                return redirect('signin')
        else:
            messages.error(request, "Invalid email or password.")
            return redirect('signin')

    # Render the sign-in form for GET requests
    return render(request, 'signin.html')




def patient_dashboard(request):
    # Retrieve the user_id from the session
    user_id = request.session.get('user_id')

    # Check if the user is logged in
    if not user_id:
        messages.error(request, 'You must be logged in to access this page.')
        return redirect('signin')  # Redirect to the login page

    try:
        # Fetch the patient's profile using the user_id
        patient_profile = PatientsProfiles.objects.get(user_id=user_id)
    except PatientsProfiles.DoesNotExist:
        messages.error(request, 'Patient profile not found.')
        return redirect('signin')  # Redirect to login if profile is missing

    # Fetch appointments for the logged-in patient
    upcoming_appointments = Appointments.objects.filter(
        patient=patient_profile, date__gte=date.today()
    ).order_by('date')

    past_appointments = Appointments.objects.filter(
        patient=patient_profile, date__lt=date.today()
    ).order_by('-date')

    # Pass the patient profile and appointments to the template
    context = {
        'patient_profile': patient_profile,
        'upcoming_appointments': upcoming_appointments,
        'past_appointments': past_appointments,
    }
    return render(request, 'patient_dashboard.html', context)
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.core.mail import EmailMessage
from django.conf import settings
from .models import DoctorsProfiles, DoctorAdditionalInfo, Appointments


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from .models import DoctorsProfiles, DoctorAdditionalInfo, Appointments
from django.core.mail import EmailMessage
from django.conf import settings
import os
import pdfkit

def doctor_dashboard(request):
    user_id = request.session.get('user_id')
    
    if not user_id:
        messages.error(request, 'You must be logged in to access this page.')
        return redirect('signin')

    try:
        doctor_profile = DoctorsProfiles.objects.get(user_id=user_id)
    except DoctorsProfiles.DoesNotExist:
        messages.error(request, 'Doctor profile not found.')
        return redirect('signin')
    
    doctor_additional_info = DoctorAdditionalInfo.objects.filter(doctor=doctor_profile).first()

    # Handle form submissions
    if request.method == 'POST':
        # Handle video link submission
        if 'appointment_id' in request.POST and 'video_link' in request.POST:
            appointment_id = request.POST.get('appointment_id')
            video_link = request.POST.get('video_link', '').strip()
            
            try:
                appointment = Appointments.objects.get(id=appointment_id, doctor=doctor_profile)
                
                if video_link:
                    if not (video_link.startswith('http://') or video_link.startswith('https://')):
                        video_link = 'https://' + video_link
                    
                    appointment.video_link = video_link
                    appointment.is_video_link_sent = True
                    appointment.save()
                    
                    send_video_link_notification(appointment)
                    messages.success(request, "Video link updated and sent to patient successfully!")
                else:
                    messages.error(request, "Please enter a valid video link")
                
            except Appointments.DoesNotExist:
                messages.error(request, "Appointment not found.")
            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
        
        # Handle prescription submission
        elif 'prescription_text' in request.POST:
            appointment_id = request.POST.get('appointment_id')
            prescription_text = request.POST.get('prescription_text')
            
            try:
                appointment = Appointments.objects.get(id=appointment_id, doctor=doctor_profile)
                appointment.prescription_text = prescription_text
                
                # Generate PDF prescription
                pdf_filename = f'prescription_{appointment.id}.pdf'
                pdf_dir = os.path.join("media", "prescriptions")
                os.makedirs(pdf_dir, exist_ok=True)
                pdf_path = os.path.join(pdf_dir, pdf_filename)
                
                pdf_content = generate_prescription_html(appointment, prescription_text)
                
                wkhtmltopdf_path = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
                config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
                
                options = {
                    'enable-local-file-access': '',
                    'quiet': '',
                    'page-size': 'A4',
                    'encoding': 'UTF-8',
                    'margin-top': '15mm',
                    'margin-right': '15mm',
                    'margin-bottom': '15mm',
                    'margin-left': '15mm'
                }
                
                try:
                    pdfkit.from_string(pdf_content, pdf_path, configuration=config, options=options)
                    appointment.prescription_file.name = f'prescriptions/{pdf_filename}'
                    messages.success(request, "Prescription saved successfully!")
                except Exception as e:
                    messages.error(request, f"PDF generation failed: {str(e)}")
                
                appointment.save()
                
            except Appointments.DoesNotExist:
                messages.error(request, "Appointment not found.")
        
        # Handle consultation completion
        elif 'complete_appointment' in request.POST:
            appointment_id = request.POST.get('appointment_id')
            try:
                appointment = Appointments.objects.get(id=appointment_id, doctor=doctor_profile)
                appointment.completed = True
                appointment.completion_date = timezone.now()
                appointment.save()
                messages.success(request, "Consultation marked as completed!")
            except Appointments.DoesNotExist:
                messages.error(request, "Appointment not found.")
        
        return redirect('doctor_dashboard')

    # Fetch appointments
    today = timezone.now().date()
    upcoming_appointments = Appointments.objects.filter(
        doctor=doctor_profile,
        date__gte=today,
        completed=False
    ).order_by('date', 'time_slot')

    past_appointments = Appointments.objects.filter(
        doctor=doctor_profile,
        date__lt=today
    ).order_by('-date', '-time_slot')

    # Count pending prescriptions
    pending_prescriptions_count = Appointments.objects.filter(
        doctor=doctor_profile,
        prescription_text__isnull=True,
        date__lte=today,
        completed=False
    ).count()

    context = {
        'doctor_profile': doctor_profile,
        'doctor_additional_info': doctor_additional_info,
        'upcoming_appointments': upcoming_appointments,
        'past_appointments': past_appointments,
        'today_appointments_count': upcoming_appointments.filter(date=today).count(),
        'upcoming_appointments_count': upcoming_appointments.count(),
        'pending_prescriptions_count': pending_prescriptions_count,
    }
    return render(request, 'doctor_dashboard.html', context)

def generate_prescription_html(appointment, prescription_text):
    current_date = timezone.now().strftime("%B %d, %Y")
    return f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
            .header {{ text-align: center; margin-bottom: 20px; }}
            .header h1 {{ color: #2c3e50; margin-bottom: 5px; }}
            .header p {{ margin: 5px 0; color: #7f8c8d; }}
            .divider {{ border-top: 2px solid #3498db; margin: 15px 0; }}
            .patient-info {{ margin-bottom: 20px; }}
            .patient-info p {{ margin: 5px 0; }}
            .prescription-content {{ margin: 20px 0; }}
            .footer {{ margin-top: 40px; text-align: right; }}
            .footer p {{ margin: 5px 0; }}
            .signature {{ margin-top: 50px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>MEDICAL PRESCRIPTION</h1>
            <p>Dr. {appointment.doctor.user.get_full_name()}</p>
            <p>{appointment.doctor.specialization}</p>
            <p>License No: {appointment.doctor.license_number}</p>
        </div>
        
        <div class="divider"></div>
        
        <div class="patient-info">
            <p><strong>Patient Name:</strong> {appointment.patient.user.get_full_name()}</p>
            <p><strong>Gender:</strong> {appointment.patient.gender}</p>
            <p><strong>Date:</strong> {current_date}</p>
        </div>
        
        <div class="divider"></div>
        
        <div class="prescription-content">
            <h3>Rx</h3>
            <p>{prescription_text}</p>
        </div>
        
        <div class="footer">
            <div class="signature">
                <p>_________________________</p>
                <p>Dr. {appointment.doctor.user.get_full_name()}</p>
                <p>{appointment.doctor.specialization}</p>
            </div>
        </div>
    </body>
    </html>
    """

def send_video_link_notification(appointment):
    subject = f"Your Video Consultation Link with Dr. {appointment.doctor.user.get_full_name()}"
    message = f"""
    Dear {appointment.patient.user.get_full_name()},
    
    Your video consultation link with Dr. {appointment.doctor.user.get_full_name()} 
    on {appointment.date} at {appointment.time_slot.strftime('%I:%M %p')} is ready.
    
    Consultation Link: {appointment.video_link}
    
    Please join on time for your appointment.
    
    Best regards,
    Healthcare Team
    """
    email = EmailMessage(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [appointment.patient.user.email]
    )
    email.send()

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
import os
import pdfkit
from django.http import FileResponse, Http404

from django.template.loader import render_to_string
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.template.loader import render_to_string  # Add this import
from django.http import FileResponse, Http404
from django.conf import settings
from .models import DoctorsProfiles, PatientsProfiles, Appointments
import os
import pdfkit

def write_prescription(request, appointment_id):
    user_id = request.session.get('user_id')
    
    if not user_id:
        messages.error(request, 'You must be logged in to access this page.')
        return redirect('signin')

    try:
        doctor_profile = DoctorsProfiles.objects.get(user_id=user_id)
    except DoctorsProfiles.DoesNotExist:
        messages.error(request, 'Doctor profile not found.')
        return redirect('signin')

    appointment = get_object_or_404(Appointments, id=appointment_id, doctor=doctor_profile)

    if request.method == "POST":
        prescription_text = request.POST.get("prescription_text", "").strip()
        
        if not prescription_text:
            messages.error(request, "Prescription text cannot be empty.")
            return redirect('write_prescription', appointment_id=appointment_id)
        
        try:
            # Generate PDF first to ensure it's valid
            pdf_filename = f'prescription_{appointment.id}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf'
            pdf_dir = os.path.join(settings.MEDIA_ROOT, 'prescriptions')
            os.makedirs(pdf_dir, exist_ok=True)
            pdf_path = os.path.join(pdf_dir, pdf_filename)

            # Generate HTML with proper error handling
            html_content = render_to_string('prescription_template.html', {
                'appointment': appointment,
                'doctor': doctor_profile,
                'prescription_text': prescription_text,
                'date': timezone.now().strftime("%B %d, %Y")
            })

            # Generate PDF with verification
            pdfkit.from_string(
                html_content,
                pdf_path,
                configuration=pdfkit.configuration(
                    wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
                ),
                options={
                    'page-size': 'A4',
                    'encoding': 'UTF-8',
                    'margin-top': '15mm',
                    'margin-right': '15mm',
                    'margin-bottom': '15mm',
                    'margin-left': '15mm'
                }
            )

            # Verify PDF was created and has content
            if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
                raise Exception("PDF generation failed - empty file created")

            # Save to database only after successful PDF generation
            appointment.prescription_text = prescription_text
            appointment.prescription_file.name = f'prescriptions/{pdf_filename}'
            appointment.save()

            messages.success(request, "Prescription generated successfully!")
            return redirect('doctor_dashboard')

        except Exception as e:
            # Clean up failed PDF file if it exists
            if 'pdf_path' in locals() and os.path.exists(pdf_path):
                os.remove(pdf_path)
            messages.error(request, f"Failed to generate prescription: {str(e)}")
            return redirect('write_prescription', appointment_id=appointment_id)

    # For GET requests
    context = {
        'appointment': appointment,
        'doctor_profile': doctor_profile,
        'current_date': timezone.now().strftime("%Y-%m-%d"),
        'existing_prescription': appointment.prescription_text or ""
    }
    return render(request, 'write_prescription.html', context)


def view_prescription(request, appointment_id):
    user_id = request.session.get('user_id')
    
    if not user_id:
        messages.error(request, 'You must be logged in to view prescriptions.')
        return redirect('signin')

    try:
        appointment = Appointments.objects.get(id=appointment_id)
        
        # Verify authorization - check if user is either the patient or doctor
        is_patient = PatientsProfiles.objects.filter(user_id=user_id, id=appointment.patient_id).exists()
        is_doctor = DoctorsProfiles.objects.filter(user_id=user_id, id=appointment.doctor_id).exists()
        
        if not (is_patient or is_doctor):
            messages.error(request, 'You are not authorized to view this prescription.')
            return redirect('dashboard')

        if not appointment.prescription_file:
            raise Http404("No prescription available")

        # Build absolute file path
        file_path = appointment.prescription_file.path
        
        if not os.path.exists(file_path):
            raise Http404("Prescription file not found")

        # Read file content and verify it's not empty
        with open(file_path, 'rb') as f:
            file_content = f.read()
            if not file_content:
                raise Http404("Prescription file is empty")

        # Serve the file with correct headers
        response = FileResponse(open(file_path, 'rb'), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="prescription_{appointment.id}.pdf"'
        return response

    except Appointments.DoesNotExist:
        messages.error(request, 'Appointment not found.')
        return redirect('dashboard')
#def doctor_dashboard(request):
    user_id = request.session.get('user_id')
    
    if not user_id:
        messages.error(request, 'You must be logged in to access this page.')
        return redirect('signin')

    try:
        doctor_profile = DoctorsProfiles.objects.get(user_id=user_id)
    except DoctorsProfiles.DoesNotExist:
        messages.error(request, 'Doctor profile not found.')
        return redirect('signin')
    
    doctor_additional_info = DoctorAdditionalInfo.objects.filter(doctor=doctor_profile).first()

    # Handle video link submission
    if request.method == 'POST' and 'appointment_id' in request.POST:
        appointment_id = request.POST.get('appointment_id')
        video_link = request.POST.get('video_link', '').strip()
        
        try:
            appointment = Appointments.objects.get(id=appointment_id, doctor=doctor_profile)
            
            # Validate and format the URL
            if video_link:
                if not (video_link.startswith('http://') or video_link.startswith('https://')):
                    video_link = 'https://' + video_link
                
                appointment.video_link = video_link
                appointment.is_video_link_sent = True
                appointment.save()
                
                # Send notification to patient
                send_video_link_notification(appointment)
                
                messages.success(request, "Video link updated and sent to patient successfully!")
                return redirect('doctor_dashboard')
            else:
                messages.error(request, "Please enter a valid video link")
                
        except Appointments.DoesNotExist:
            messages.error(request, "Appointment not found.")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")

    # Fetch appointments
    upcoming_appointments = Appointments.objects.filter(
        doctor=doctor_profile,
        date__gte=timezone.now().date()
    ).order_by('date', 'time_slot')

    past_appointments = Appointments.objects.filter(
        doctor=doctor_profile,
        date__lt=timezone.now().date()
    ).order_by('-date', '-time_slot')

    context = {
        'doctor_profile': doctor_profile,
        'doctor_additional_info': doctor_additional_info,
        'upcoming_appointments': upcoming_appointments,
        'past_appointments': past_appointments,
        'today_appointments_count': upcoming_appointments.filter(date=timezone.now().date()).count(),
        'upcoming_appointments_count': upcoming_appointments.count(),
    }
    return render(request, 'doctor_dashboard.html', context)

#def send_video_link_notification(appointment):
    subject = f"Your Video Consultation Link with Dr. {appointment.doctor.user.get_full_name()}"
    message = f"""
    Dear {appointment.patient.user.get_full_name()},
    
    Your video consultation link with Dr. {appointment.doctor.user.get_full_name()} 
    on {appointment.date} at {appointment.time_slot.strftime('%I:%M %p')} is ready.
    
    Consultation Link: {appointment.video_link}
    
    Please join on time for your appointment.
    
    Best regards,
    Healthcare Team
    """
    email = EmailMessage(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [appointment.patient.user.email]
    )
    email.send()



from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from datetime import datetime, time, timedelta
from .models import PatientsProfiles, DoctorsProfiles, Appointments

def book_appointment(request):
    user_id = request.session.get('user_id')
    
    if not user_id:
        messages.error(request, "Please log in to book an appointment.")
        return redirect('signin')

    try:
        patient = PatientsProfiles.objects.get(user_id=user_id)
    except PatientsProfiles.DoesNotExist:
        messages.error(request, "Complete your profile before booking an appointment.")
        return redirect('signup')

    specializations = DoctorsProfiles.objects.filter(approved=True).values_list('specialization', flat=True).distinct()
    approved_doctors = DoctorsProfiles.objects.filter(approved=True)

    if request.method == 'POST':
        doctor_id = request.POST.get('doctor_id')
        date = request.POST.get('date')

        try:
            doctor = DoctorsProfiles.objects.get(id=doctor_id)

            # Check the doctor's available days
            available_days = [day.strip().lower() for day in doctor.available_days.split(',')]
            appointment_day = datetime.strptime(date, '%Y-%m-%d').strftime('%A').lower()
            
            if appointment_day not in available_days:
                messages.error(request, f"Dr. {doctor.user} is not available on {appointment_day.capitalize()}s.")
                return redirect('book_appointment')

            # Check appointment limit
            appointments_count = Appointments.objects.filter(doctor=doctor, date=date).count()
            if appointments_count >= 10:
                messages.error(request, f"All slots are booked for Dr. {doctor.user} on {date}.")
                return redirect('book_appointment')

            # Assign token number and time slot
            token_number = appointments_count + 1
            time_slot = (datetime.combine(datetime.today(), time(9, 0)) + 
                        timedelta(minutes=(token_number - 1) * 30)).time()

            # Create the appointment
            appointment = Appointments.objects.create(
                doctor=doctor,
                patient=patient,
                date=date,
                token_number=token_number,
                time_slot=time_slot,
                payment_status='Pending',
                amount_paid=200.00
            )

            # Redirect to payment page with appointment ID
            return redirect('payment', appointment_id=appointment.id)

        except DoctorsProfiles.DoesNotExist:
            messages.error(request, "Invalid doctor selection. Please try again.")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")

    context = {
        'approved_doctors': approved_doctors,
        'specializations': specializations,
        'RAZORPAY_KEY_ID': settings.RAZORPAY_KEY_ID,
    }
    return render(request, 'book_appointment.html', context)
#def book_appointment(request):
    user_id = request.session.get('user_id')
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    if not user_id:
        messages.error(request, "Please log in to book an appointment.")
        return redirect('signin')

    try:
        patient = PatientsProfiles.objects.get(user_id=user_id)
    except PatientsProfiles.DoesNotExist:
        messages.error(request, "Complete your profile before booking an appointment.")
        return redirect('signup')

    specializations = DoctorsProfiles.objects.filter(approved=True).values_list('specialization', flat=True).distinct()
    approved_doctors = DoctorsProfiles.objects.filter(approved=True)

    if request.method == 'POST':
        doctor_id = request.POST['doctor_id']
        date = request.POST['date']

        try:
            doctor = DoctorsProfiles.objects.get(id=doctor_id)

            # Check the doctor's available days
            available_days = doctor.available_days.split(', ')
            appointment_day = datetime.strptime(date, '%Y-%m-%d').strftime('%A')
            
            if appointment_day not in available_days:
                messages.error(request, f"Dr. {doctor.user} is not available on {appointment_day}s.")
                return redirect('book_appointment')

            # Check appointment limit
            appointments_count = Appointments.objects.filter(doctor=doctor, date=date).count()
            if appointments_count >= 10:
                messages.error(request, f"All slots are booked for Dr. {doctor.user} on {date}.")
                return redirect('book_appointment')

            # Assign token number and time slot
            token_number = appointments_count + 1
            time_slot = (datetime.combine(datetime.today(), time(9, 0)) + 
                        timedelta(minutes=(token_number - 1) * 30)).time()

            # Create the appointment
            appointment = Appointments.objects.create(
                doctor=doctor,
                patient=patient,
                date=date,
                token_number=token_number,
                time_slot=time_slot,
                payment_status='Pending',
                amount_paid=200.00
            )

            messages.success(request, f"Appointment booked with Dr. {doctor.user} at {time_slot}. Complete payment to confirm.")
            return redirect('payment', appointment_id=appointment.id)

        except DoctorsProfiles.DoesNotExist:
            messages.error(request, "Invalid doctor selection. Please try again.")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")

    context = {
        'approved_doctors': approved_doctors,
        'specializations': specializations,
    }
    return render(request, 'book_appointment.html', context)


#def doctor_dashboard(request):
    user_id = request.session.get('user_id')

    if not user_id:
        messages.error(request, 'You must be logged in to access this page.')
        return redirect('signin')

    try:
        doctor_profile = DoctorsProfiles.objects.get(user_id=user_id)
    except DoctorsProfiles.DoesNotExist:
        messages.error(request, 'Doctor profile not found.')
        return redirect('signin')
    doctor_additional_info = DoctorAdditionalInfo.objects.filter(doctor=doctor_profile).first()

    # Fetch upcoming and past appointments
    upcoming_appointments = Appointments.objects.filter(
        doctor=doctor_profile, date__gte=now().date()
    ).order_by('date', 'time_slot')  # Use 'time_slot' instead of 'time'


    past_appointments = Appointments.objects.filter(
        doctor=doctor_profile, date__lt=now().date()
    ).order_by('-date', '-time_slot')

    context = {
        'doctor_profile': doctor_profile,
        'doctor_additional_info' : doctor_additional_info,
        'upcoming_appointments': upcoming_appointments,
        'past_appointments': past_appointments,
    }
    return render(request, 'doctor_dashboard.html', context)

def doctor_profile(request):
    user_id = request.session.get('user_id')

    if not user_id:
        messages.error(request, 'You must be logged in to access this page.')
        return redirect('signin')

    # Fetch the doctor's profile and additional info
    doctor_profile = DoctorsProfiles.objects.filter(user_id=user_id).first()
    doctor_additional_info = DoctorAdditionalInfo.objects.filter(doctor=doctor_profile).first() if doctor_profile else None

    if request.method == 'POST':
        specialization = request.POST.get('specialization', '').strip()
        experience_years = request.POST.get('experience_years', '0').strip()
        hospital = request.POST.get('hospital', '').strip()
        hospitals = request.POST.get('hospitals', '').strip()
        qualifications = request.POST.get('qualifications', '').strip()
        bio = request.POST.get('bio', '').strip()
        profile_image = request.FILES.get('profile_image')

        # Create or update doctor profile
        if not doctor_profile:
            doctor_profile = DoctorsProfiles.objects.create(
                user_id=user_id,
                specialization=specialization,
                experience_years=experience_years,
                hospital=hospital,
                profile_image=profile_image if profile_image else None
            )
        else:
            doctor_profile.specialization = specialization
            doctor_profile.experience_years = experience_years
            doctor_profile.hospital = hospital
            if profile_image:
                doctor_profile.profile_image = profile_image
            doctor_profile.save()  # Save doctor profile changes

        # Create or update doctor additional info
        if not doctor_additional_info:
            doctor_additional_info = DoctorAdditionalInfo.objects.create(
                doctor=doctor_profile,
                hospitals=hospitals,
                qualifications=qualifications,
                bio=bio,
                profile_image=profile_image if profile_image else None  # Store image here as well
            )
        else:
            doctor_additional_info.hospitals = hospitals
            doctor_additional_info.qualifications = qualifications
            doctor_additional_info.bio = bio
            if profile_image:
                doctor_additional_info.profile_image = profile_image  # Update image in additional info
            doctor_additional_info.save()  # Save additional info changes

        messages.success(request, "Profile updated successfully.")
        return redirect('doctor_dashboard')  # Redirect to the dashboard after saving

    context = {
        'doctor_profile': doctor_profile,
        'doctor_additional_info': doctor_additional_info,
    }
    return render(request, 'doctor_profile.html', context)

#def write_prescription(request, appointment_id):
    appointment = get_object_or_404(Appointments, id=appointment_id)

    if request.method == "POST":
        prescription_text = request.POST.get("prescription_text")
        appointment.prescription_text = prescription_text

        # Define file paths
        pdf_filename = f'prescription_{appointment.id}.pdf'
        pdf_dir = os.path.join("media", "prescriptions")
        os.makedirs(pdf_dir, exist_ok=True)  # Ensure directory exists
        pdf_path = os.path.join(pdf_dir, pdf_filename)

        # Get current date
        current_date = timezone.now().strftime("%B %d, %Y")
        
        # Generate professional HTML content for PDF
        pdf_content = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                .header {{ text-align: center; margin-bottom: 20px; }}
                .header h1 {{ color: #2c3e50; margin-bottom: 5px; }}
                .header p {{ margin: 5px 0; color: #7f8c8d; }}
                .divider {{ border-top: 2px solid #3498db; margin: 15px 0; }}
                .patient-info {{ margin-bottom: 20px; }}
                .patient-info p {{ margin: 5px 0; }}
                .prescription-content {{ margin: 20px 0; }}
                .footer {{ margin-top: 40px; text-align: right; }}
                .footer p {{ margin: 5px 0; }}
                .signature {{ margin-top: 50px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>MEDICAL PRESCRIPTION</h1>
                <p>Dr. {appointment.doctor.user.get_full_name()}</p>
                <p>{appointment.doctor.specialization}</p>
                <p>License No: {appointment.doctor.license_number}</p>
            </div>
            
            <div class="divider"></div>
            
            <div class="patient-info">
                <p><strong>Patient Name:</strong> {appointment.patient.user.get_full_name()}</p>
                <p><strong>Gender:</strong> {appointment.patient.gender}</p>
                <p><strong>Date:</strong> {current_date}</p>
            </div>
            
            <div class="divider"></div>
            
            <div class="prescription-content">
                <h3>Rx</h3>
                <p>{prescription_text}</p>
            </div>
            
            <div class="footer">
                <div class="signature">
                    <p>_________________________</p>
                    <p>Dr. {appointment.doctor.user.get_full_name()}</p>
                    <p>{appointment.doctor.specialization}</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Path to wkhtmltopdf
        wkhtmltopdf_path = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
        config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)

        # PDFKit options
        options = {
            'enable-local-file-access': '',
            'quiet': '',
            'page-size': 'A4',
            'encoding': 'UTF-8',
            'margin-top': '15mm',
            'margin-right': '15mm',
            'margin-bottom': '15mm',
            'margin-left': '15mm'
        }

        try:
            pdfkit.from_string(pdf_content, pdf_path, configuration=config, options=options)
        except OSError as e:
            messages.error(request, f"PDF generation failed: {str(e)}")
            return redirect("write_prescription", appointment_id=appointment_id)

        # Save file path in the database
        appointment.prescription_file.name = f'prescriptions/{pdf_filename}'
        appointment.save()

        messages.success(request, "Prescription saved successfully!")
        return redirect("write_prescription", appointment_id=appointment_id)

    return render(request, "write_prescription.html", {"appointment": appointment})
#def write_prescription(request, appointment_id):
    appointment = get_object_or_404(Appointments, id=appointment_id)

    if request.method == "POST":
        prescription_text = request.POST.get("prescription_text")
        appointment.prescription_text = prescription_text

        # Define file paths
        pdf_filename = f'prescription_{appointment.id}.pdf'
        pdf_dir = os.path.join("media", "prescriptions")
        os.makedirs(pdf_dir, exist_ok=True)  # Ensure directory exists
        pdf_path = os.path.join(pdf_dir, pdf_filename)

        # Generate HTML content for PDF
        pdf_content = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; }}
                h2 {{ color: #333; }}
                p {{ font-size: 14px; }}
            </style>
        </head>
        <body>
            <h2>Prescription for {appointment.patient.user}</h2>
            <p>{prescription_text}</p>
        </body>
        </html>
        """

        # Path to wkhtmltopdf
        wkhtmltopdf_path = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
        config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)

        # PDFKit options
        options = {
            'enable-local-file-access': '',
            'quiet': '',
            'page-size': 'A4',
            'encoding': 'UTF-8'
        }

        try:
            pdfkit.from_string(pdf_content, pdf_path, configuration=config, options=options)
        except OSError as e:
            messages.error(request, f"PDF generation failed: {str(e)}")
            return redirect("write_prescription", appointment_id=appointment_id)

        # Save file path in the database
        appointment.prescription_file.name = f'prescriptions/{pdf_filename}'
        appointment.save()

        messages.success(request, "Prescription saved successfully!")  # Success message
        return redirect("write_prescription", appointment_id=appointment_id)

    return render(request, "write_prescription.html", {"appointment": appointment})


#def view_prescription(request, appointment_id):
    appointment = get_object_or_404(Appointments, id=appointment_id)

    if not appointment.prescription_file:
        return JsonResponse({"error": "No prescription available."}, status=404)

    file_path = appointment.prescription_file.path

    if os.path.exists(file_path):
        return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=os.path.basename(file_path))
    else:
        raise Http404("File not found")


# Home page
def index(request):
    return render(request, "index.html")

def about(request):
    return render(request, 'about.html')

def service(request):
    return render(request, 'service.html')

def department(request):
    return render(request, 'department.html')

def doctor(request):
    approved_doctors = DoctorsProfiles.objects.filter(approved=True)  # Fetch only approved doctors
    return render(request, 'doctor.html', {'doctors': approved_doctors})

def doctorsdetails(request, doctor_id):
    """
    Display detailed information about a selected doctor.
    """
    doctor = get_object_or_404(DoctorsProfiles, id=doctor_id)
    additional_info = DoctorAdditionalInfo.objects.filter(doctor=doctor).first()
    
    return render(request, 'doctorsdetails.html', {
        'doctor': doctor,
        'additional_info': additional_info
    })


def appointment(request):
    return render(request, 'appointment.html')

def contact(request):
    return render(request, 'contact.html')



def registration_success(request):
    return render(request, 'registration_success.html')


def logout_view(request):
    
    logout(request)  # Log out the user
    messages.success(request, "You have been logged out successfully.")  # Optional: Add a logout success message
    return redirect('signin')

def payment_success(request):
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    if request.method == 'POST':
        try:
            # Verify payment signature
            params_dict = {
                'razorpay_order_id': request.POST.get('razorpay_order_id'),
                'razorpay_payment_id': request.POST.get('razorpay_payment_id'),
                'razorpay_signature': request.POST.get('razorpay_signature')
            }
            
            client.utility.verify_payment_signature(params_dict)

            # Update appointment
            appointment = Appointments.objects.get(
                razorpay_order_id=params_dict['razorpay_order_id'],
                payment_status='Pending'
            )
            
            # Assign token number and time slot
            appointments_count = Appointments.objects.filter(
                doctor=appointment.doctor,
                date=appointment.date,
                payment_status='Completed'
            ).count()
            
            token_number = appointments_count + 1
            time_slot = (datetime.combine(datetime.today(), time(9, 0)) + 
                       timedelta(minutes=(token_number - 1) * 30)).time()

            appointment.token_number = token_number
            appointment.time_slot = time_slot
            appointment.payment_status = 'Completed'
            appointment.razorpay_payment_id = params_dict['razorpay_payment_id']
            appointment.video_link = f"https://meet.google.com/{appointment.doctor.user.username}-{appointment.date.strftime('%Y%m%d')}"
            appointment.save()

            # Send confirmation email
            send_confirmation_email(appointment)

            return JsonResponse({
                'status': 'success',
                'appointment_id': appointment.id
            })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)

    return redirect('book_appointment')

def send_confirmation_email(appointment):
    subject = 'Appointment Confirmation'
    message = f"""
    Dear {appointment.patient.user.get_full_name()},
    
    Your appointment with {appointment.doctor.user} is confirmed.
    
    Date: {appointment.date}
    Time: {appointment.time_slot.strftime('%I:%M %p')}
    Token Number: {appointment.token_number}
    
    Video Consultation Link: {appointment.video_link}
    
    Thank you for choosing our service.
    """
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [appointment.patient.user.email]
    
    send_mail(subject, message, from_email, recipient_list)


def edit_doctor(request, doctor_id):
    doctor = get_object_or_404(DoctorsProfiles, id=doctor_id)
    if request.method == "POST":
        doctor.specialization = request.POST.get("specialization")
        doctor.experience_years = request.POST.get("experience_years")
        doctor.hospital = request.POST.get("hospital")
        doctor.save()
        messages.success(request, "Doctor details updated successfully.")
        return redirect(reverse("admin_dashboard"))
    return render(request, "edit_doctor.html", {"doctor": doctor})

def delete_doctor(request, doctor_id):
    doctor = get_object_or_404(DoctorsProfiles, id=doctor_id)
    doctor.delete()
    messages.success(request, "Doctor deleted successfully.")
    return redirect(reverse("admin_dashboard"))

def approve_doctor(request, doctor_id):
    doctor = get_object_or_404(DoctorsProfiles, id=doctor_id)
    doctor.approved = True
    doctor.save()

    # Send approval email
    send_mail(
        subject="Approval Notification",
        message=f"Dear {doctor.user},\n\nYour profile has been approved. You can now access the full features of our platform.\n\nBest Regards,\nAdmin Team",
        from_email="nihalabinthsalih786@gmail.com",
        recipient_list=[doctor.user.email],
        fail_silently=False,
    )

    messages.success(request, f"Doctor {doctor.user} approved and notified via email.")
    return redirect(reverse("admin_dashboard"))

def admin_dashboard(request):
    doctors = DoctorsProfiles.objects.all()
    patients = PatientsProfiles.objects.all()
    appointments = Appointments.objects.all()
    medicines = Medicine.objects.all()  # Fetch all medicines
    products = Products.objects.all()
    orders = Orders.objects.all().order_by('-created_at')
    brand =Brand.objects.all()
    pending_approvals_count = doctors.filter(approved=False).count()

    return render(request, "admin_dashboard.html", {
        "doctors": doctors,
        "patients": patients,
        "appointments": appointments,
        "medicines": medicines,  # Add medicines to the context
        "products": products,
        "brand" : "brand",
        "orders": orders,
        "pending_approvals_count": pending_approvals_count,
    })


def add_medicine(request): 
    if request.method == "POST":
        name = request.POST.get("name")
        brand_name = request.POST.get("brand")
        description = request.POST.get("description")
        dosage = request.POST.get("dosage")
        price = request.POST.get("price")
        stock = request.POST.get("stock")
        manufacturer = request.POST.get("manufacturer")
        manufacturer_address = request.POST.get("manufacturer_address", "thrissur round, kerala")  # Default value
        expiry_date = request.POST.get("expiry_date")
        category = request.POST.get("category")
        prescription_required = request.POST.get("prescription_required") == "on"
        image = request.FILES.get("image")

        # Additional fields
        key_benefits = request.POST.get("key_benefits")
        how_to_use = request.POST.get("how_to_use")
        safety_information = request.POST.get("safety_information")
        other_information = request.POST.get("other_information")

        # Convert expiry_date to DateField format
        try:
            expiry_date = datetime.strptime(expiry_date, "%Y-%m-%d").date()
        except ValueError:
            return render(request, "add_medicine.html", {"error": "Invalid expiry date format."})

        # Convert price and stock to proper types
        try:
            price = float(price)
            stock = int(stock)
        except ValueError:
            return render(request, "add_medicine.html", {"error": "Invalid price or stock value."})

        # Get or create Brand instance
        brand, created = Brand.objects.get_or_create(name=brand_name)

        # Save medicine
        medicine = Medicine(
            name=name,
            brand=brand,
            description=description,
            dosage=dosage,
            price=price,
            stock=stock,
            manufacturer=manufacturer,
            manufacturer_address=manufacturer_address,
            expiry_date=expiry_date,
            category=category,
            prescription_required=prescription_required,
            image=image,
            key_benefits=key_benefits,
            how_to_use=how_to_use,
            safety_information=safety_information,
            other_information=other_information
        )
        medicine.save()

        # **Redirect to avoid stale data issue**
        return redirect("admin_dashboard")  # Make sure "admin_dashboard" is the correct URL name

    medicines = Medicine.objects.all()
    return render(request, "admin_dashboard.html", {"medicines": medicines})

def delete_medicine(request, medicine_id):
    medicine = get_object_or_404(Medicine, id=medicine_id)
    medicine.delete()
    messages.success(request, "medicine deleted successfully.")
    return redirect(reverse("admin_dashboard"))


def edit_medicine(request, medicine_id):
    medicine = get_object_or_404(Medicine, id=medicine_id)  # Get the medicine object

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        brand_name = request.POST.get("brand", "").strip()
        description = request.POST.get("description", "").strip()
        dosage = request.POST.get("dosage", "").strip()
        price = request.POST.get("price", "0").strip()
        stock = request.POST.get("stock", "0").strip()
        manufacturer = request.POST.get("manufacturer", "").strip()
        manufacturer_address = request.POST.get("manufacturer_address", "").strip()
        expiry_date = request.POST.get("expiry_date", "").strip()
        category_name = request.POST.get("category", "").strip()
        key_benefits = request.POST.get("key_benefits", "").strip()
        how_to_use = request.POST.get("how_to_use", "").strip()
        safety_information = request.POST.get("safety_information", "").strip()
        other_information = request.POST.get("other_information", "").strip()
        prescription_required = request.POST.get("prescription_required") == "on"
        image = request.FILES.get("image")

        # Ensure manufacturer_address is not empty (Avoid NOT NULL constraint error)
        if not manufacturer_address:
            manufacturer_address = "Unknown Address"  # Set a default value

        # Convert expiry_date to DateField format
        try:
            expiry_date = datetime.strptime(expiry_date, "%Y-%m-%d").date()
        except ValueError:
            return render(request, "edit_medicine.html", {"medicine": medicine, "error": "Invalid expiry date format."})

        # Get or create the Brand instance
        brand, _ = Brand.objects.get_or_create(name=brand_name)

        # Get or create the Category instance

        # Update the medicine instance
        medicine.name = name
        medicine.brand = brand
        medicine.description = description
        medicine.dosage = dosage
        medicine.price = float(price) if price else 0.0  # Ensure price is a valid float
        medicine.stock = int(stock) if stock else 0  # Ensure stock is an integer
        medicine.manufacturer = manufacturer
        medicine.manufacturer_address = manufacturer_address  # Ensuring NOT NULL value
        medicine.expiry_date = expiry_date
        medicine.category = category_name  # Ensure it stores a Category instance
        medicine.key_benefits = key_benefits
        medicine.how_to_use = how_to_use
        medicine.safety_information = safety_information
        medicine.other_information = other_information
        medicine.prescription_required = prescription_required

        # Update image only if a new one is uploaded
        if image:
            medicine.image = image

        medicine.save()  # Save the updated medicine details

        return redirect("admin_dashboard")  # Redirect back to the dashboard

    return render(request, "edit_medicine.html", {"medicine": medicine})


def add_product(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        price = request.POST.get('price')
        discount_price = request.POST.get('discount_price')
        category = request.POST.get('category')
        stock = request.POST.get('stock')
        is_trending = 'is_trending' in request.POST
        image = request.FILES.get('image')

        product = Products(
            name=name,
            description=description,
            price=price,
            discount_price=discount_price if discount_price else None,
            category=category,
            stock=stock,
            is_trending=is_trending,
            image=image
        )
        product.save()
        messages.success(request, 'Product added successfully!')
        return redirect('admin_dashboard')

    return redirect('admin_dashboard')

def edit_product(request, product_id):
    product = get_object_or_404(Products, id=product_id)
    
    if request.method == 'POST':
        product.name = request.POST.get('name')
        product.description = request.POST.get('description')
        product.price = request.POST.get('price')
        product.discount_price = request.POST.get('discount_price') or None
        product.category = request.POST.get('category')
        product.stock = request.POST.get('stock')
        product.is_trending = 'is_trending' in request.POST
        
        if 'image' in request.FILES:
            product.image = request.FILES['image']
        
        product.save()
        messages.success(request, 'Product updated successfully!')
        return redirect('admin_dashboard')
    
    return redirect('admin_dashboard')

def delete_product(request, product_id):
    product = get_object_or_404(Products, id=product_id)
    
    try:
        with transaction.atomic():
            # First, update or delete related order items
            OrderItem.objects.filter(product=product).update(product=None)
            product.delete()
            messages.success(request, "Product deleted successfully")
    except Exception as e:
        messages.error(request, f"Could not delete product: {str(e)}")
    
    return redirect('admin_dashboard') 
def order_detail(request, pk):
    order = get_object_or_404(Orders, pk=pk)
    return render(request, 'admin_dashboard.html', {'order': order})

def update_order_status(request, pk, status):
    order = get_object_or_404(Orders, pk=pk)
    order.status = status
    order.save()
    messages.success(request, f'Order status updated to {status}.')
    return redirect('admin_dashboard')

#def book_appointment(request):
    user_id = request.session.get('user_id')
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


    if not user_id:
        messages.error(request, "Please log in to book an appointment.")
        return redirect('signin')

    try:
        patient = PatientsProfiles.objects.get(user_id=user_id)
    except PatientsProfiles.DoesNotExist:
        messages.error(request, "Complete your profile before booking an appointment.")
        return redirect('signup')

    specializations = DoctorsProfiles.objects.filter(approved=True).values_list('specialization', flat=True).distinct()
    approved_doctors = DoctorsProfiles.objects.filter(approved=True)

    available_dates = []

    if request.method == 'POST':
        doctor_id = request.POST['doctor_id']
        date = request.POST['date']

        try:
            doctor = DoctorsProfiles.objects.get(id=doctor_id)

            # Check the doctor's available days
            available_days = doctor.available_days.split(', ')
            today = datetime.today()

            # Generate available dates for the next 30 days based on available days
            for i in range(30):
                check_date = today + timedelta(days=i)
                if check_date.strftime('%A') in available_days:
                    available_dates.append(check_date.strftime('%Y-%m-%d'))

    

            # Check if there are already 10 appointments for the selected doctor on that date
            appointments_count = Appointments.objects.filter(doctor=doctor, date=date).count()
            if appointments_count >= 10:
                messages.error(request, f"All slots are booked for Dr. {doctor.user} on {date}.")
                return redirect('book_appointment')

            # Assign token number and time slot (30 minutes interval)
            token_number = appointments_count + 1
            time_slot = (datetime.combine(datetime.today(), time(9, 0)) + timedelta(minutes=(token_number - 1) * 30)).time()

            # Create the appointment
            appointment = Appointments.objects.create(
                doctor=doctor,
                patient=patient,
                date=date,
                token_number=token_number,
                time_slot=time_slot,
                payment_status='Pending',
                amount_paid=200.00,  # Fixed fee
                video_link=f"https://meet.google.com/{doctor.user.username}-{date.replace('-', '')}"
            )

            # Redirect to payment page
            messages.success(request, f"Appointment booked with Dr. {doctor.user} at {time_slot}. Complete payment to confirm.")
            return redirect('payment', appointment_id=appointment.id)

        except DoctorsProfiles.DoesNotExist:
            messages.error(request, "Invalid doctor selection. Please try again.")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")

    context = {
        'approved_doctors': approved_doctors,
        'specializations': specializations,
        'available_dates': available_dates,  # Pass available dates to the template
    }

    return render(request, 'book_appointment.html', context)
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

def payment(request, appointment_id):
    # Check if the user is logged in via session
    user_id = request.session.get('user_id')
    
    if not user_id:
        messages.error(request, "Please log in to proceed with payment.")
        return redirect('login')

    try:
        # Retrieve the appointment for the logged-in user
        appointment = Appointments.objects.get(id=appointment_id, patient__user_id=user_id)
        patient = PatientsProfiles.objects.get(user_id=user_id)
    except (Appointments.DoesNotExist, PatientsProfiles.DoesNotExist):
        messages.error(request, "Invalid appointment.")
        return redirect('book_appointment')

    # Initialize Razorpay client
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    
    # Create a Razorpay Order
    razorpay_order = client.order.create({
        'amount': int(float(appointment.amount_paid) * 100),  # Convert to paise
        'currency': 'INR',
        'receipt': f'appt_{appointment.id}',
        'notes': {
            'appointment_id': appointment.id,
            'patient_id': patient.id
        }
    })

    context = {
        'appointment': appointment,
        'fixed_fee': appointment.amount_paid,
        'patient': patient,
        'RAZORPAY_KEY_ID': settings.RAZORPAY_KEY_ID,
        'razorpay_order_id': razorpay_order['id']
    }
    
    return render(request, 'payment.html', context)

def payment_success(request, appointment_id):
    try:
        appointment = Appointments.objects.get(id=appointment_id)
        appointment.payment_status = 'Completed'
        appointment.save()
        messages.success(request, "Payment successful! Your appointment is confirmed.")
        return redirect('patient_dashboard')
    except Appointments.DoesNotExist:
        messages.error(request, "Invalid appointment.")
        return redirect('book_appointment')

def payment_failed(request, appointment_id):
    messages.error(request, "Payment failed. Please try again.")
    return redirect('payment', appointment_id=appointment_id)
#def payment(request, appointment_id):
    # Check if the user is logged in via session
    user_id = request.session.get('user_id')  # Retrieve the user's ID from the session

    if not user_id:
        messages.error(request, "Please log in to proceed with payment.")
        return redirect('login')  # Redirect to login page if no session ID is found

    try:
        # Retrieve the appointment for the logged-in user
        appointment = Appointments.objects.get(id=appointment_id, patient__user_id=user_id)
    except Appointments.DoesNotExist:
        messages.error(request, "Invalid appointment.")
        return redirect('book_appointment')

    if request.method == 'POST':
        # Simulate payment success
        payment_successful = True  # Replace with a real payment gateway integration
        if payment_successful:
            appointment.payment_status = 'Completed'
            appointment.save()
            messages.success(request, "Payment successful! Your appointment is confirmed.")
            return redirect('dashboard')  # Redirect to user dashboard or confirmation page
        else:
            messages.error(request, "Payment failed. Please try again.")

    context = {
        'appointment': appointment,
        'fixed_fee': 200.00,  # Pass the fixed fee to the template
    }
    return render(request, 'payment.html', context)

# Initialize Razorpay client

#def book_appointment(request):
    user_id = request.session.get('user_id')

    if not user_id:
        messages.error(request, "Please log in to book an appointment.")
        return redirect('signin')

    try:
        patient = PatientsProfiles.objects.get(user_id=user_id)
    except PatientsProfiles.DoesNotExist:
        messages.error(request, "Complete your profile before booking an appointment.")
        return redirect('signup')

    specializations = DoctorsProfiles.objects.filter(approved=True).values_list('specialization', flat=True).distinct()
    approved_doctors = DoctorsProfiles.objects.filter(approved=True)

    if request.method == 'POST':
        doctor_id = request.POST.get('doctor_id')
        date = request.POST.get('date')

        try:
            doctor = DoctorsProfiles.objects.get(id=doctor_id)

            # Check availability
            available_days = [day.strip().lower() for day in doctor.available_days.split(',')]
            selected_day = datetime.strptime(date, '%Y-%m-%d').strftime('%A').lower()
            
            if selected_day not in available_days:
                return JsonResponse({
                    'status': 'error',
                    'message': f"Dr. {doctor.user} is not available on {selected_day.capitalize()}s."
                }, status=400)

            # Check appointment slots
            appointments_count = Appointments.objects.filter(doctor=doctor, date=date).count()
            if appointments_count >= 10:
                return JsonResponse({
                    'status': 'error',
                    'message': f"All slots are booked for Dr. {doctor.user} on {date}."
                }, status=400)

            # Create order in Razorpay
            amount = 20000  # 200 INR in paise
            order = client.order.create({
                'amount': amount,
                'currency': 'INR',
                'payment_capture': '1'
            })

            # Create temporary appointment
            appointment = Appointments.objects.create(
                doctor=doctor,
                patient=patient,
                date=date,
                payment_status='Pending',
                razorpay_order_id=order['id'],
                amount=amount/100  # Convert to rupees
            )

            return JsonResponse({
                'status': 'success',
                'order_id': order['id'],
                'amount': amount,
                'currency': 'INR',
                'key': settings.RAZORPAY_KEY_ID,
                'appointment_id': appointment.id,
                'doctor_name': f"Dr. {doctor.user}",
                'date': date,
                'patient_name': patient.user.get_full_name(),
                'patient_email': patient.user.email
            })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)

    context = {
        'approved_doctors': approved_doctors,
        'specializations': specializations,
    }
    return render(request, 'book_appointment.html', context)

def patient_appointments(request):
    appointments = Appointments.objects.filter(patient__user=request.user).order_by('-date', '-time_slot')
    return render(request, 'patient_appointments.html', {'appointments': appointments})

#def doctor_dashboard(request):
    user_id = request.session.get('user_id')
    
    if not user_id:
        messages.error(request, 'You must be logged in to access this page.')
        return redirect('signin')

    try:
        doctor_profile = DoctorsProfiles.objects.get(user_id=user_id)
    except DoctorsProfiles.DoesNotExist:
        messages.error(request, 'Doctor profile not found.')
        return redirect('signin')
    
    doctor_additional_info = DoctorAdditionalInfo.objects.filter(doctor=doctor_profile).first()

    # Handle video link submission
    if request.method == 'POST' and 'appointment_id' in request.POST:
        appointment_id = request.POST.get('appointment_id')
        video_link = request.POST.get('video_link')
        
        try:
            appointment = Appointments.objects.get(id=appointment_id, doctor=doctor_profile)
            appointment.video_link = video_link
            appointment.is_video_link_sent = True
            appointment.save()
            
            # Send notification to patient
            send_video_link_notification(appointment)
            
            messages.success(request, "Video link updated and sent to patient.")
            return redirect('doctor_dashboard')
        except Appointments.DoesNotExist:
            messages.error(request, "Appointment not found.")

    # Fetch appointments
    upcoming_appointments = Appointments.objects.filter(
        doctor=doctor_profile,
        date__gte=timezone.now().date()
    ).order_by('date', 'time_slot')

    past_appointments = Appointments.objects.filter(
        doctor=doctor_profile,
        date__lt=timezone.now().date()
    ).order_by('-date', '-time_slot')

    context = {
        'doctor_profile': doctor_profile,
        'doctor_additional_info': doctor_additional_info,
        'upcoming_appointments': upcoming_appointments,
        'past_appointments': past_appointments,
    }
    return render(request, 'doctor_dashboard.html', context)

#def send_video_link_notification(appointment):
    subject = f"Your Video Consultation Link with Dr. {appointment.doctor.user.get_full_name()}"
    message = f"""
    Dear {appointment.patient.user.get_full_name()},
    
    Your video consultation link with Dr. {appointment.doctor.user.get_full_name()} 
    on {appointment.date} at {appointment.time_slot.strftime('%I:%M %p')} is ready.
    
    Consultation Link: {appointment.video_link}
    
    Please join on time for your appointment.
    
    Best regards,
    Healthcare Team
    """
    email = EmailMessage(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [appointment.patient.user.email]
    )
    email.send()

    
