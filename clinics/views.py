
from datetime import date
import os
import logging
logger = logging.getLogger("django")
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg
from django.contrib.auth import login
from django.core.files.storage import FileSystemStorage
from django.views.decorators.http import require_POST
from accounts.forms import UserCreationForm
from patients.models import Patient, MedicalRecord
from .forms import AppointmentForm, ClinicSignUpForm, ClinicGalleryForm, ClinicServiceForm, ClinicUpdateForm
from .models import Appointment, Clinic, ClinicGallery, ClinicService
from posts.models import Post, Comment

# Import Review from the new reviews app
from reviews.models import Review

# Clinic dashboard view (restored)
@login_required
def clinic_dashboard_view(request):
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')
    clinic = get_object_or_404(Clinic, user=request.user)
    assigned_patients = Appointment.objects.filter(clinic=clinic).select_related('patient')
    # Build a deduplicated list of assignments keyed by patient so each patient appears once
    ordered_assignments = assigned_patients.order_by('-created_at')
    unique_assignments_map = {}
    for appt in ordered_assignments:
        pid = getattr(appt, 'patient_id', None)
        if pid and pid not in unique_assignments_map:
            unique_assignments_map[pid] = appt
    # Keep only up to 5 unique patient assignments for dashboard display
    assigned_patients_unique = list(unique_assignments_map.values())[:5]
    appointments = Appointment.objects.filter(clinic=clinic)
    total_appointments = appointments.count()
    pending_appointments = appointments.filter(status='pending').count()
    confirmed_appointments = appointments.filter(status='confirmed').count()
    recent_appointments = appointments.select_related('patient', 'medical_record').order_by('-created_at')[:5]
    total_patients = assigned_patients.count()
    # Build lists of patients who have had any appointments with this clinic.
    # We don't care about booking status — include patients from any appointment.
    # Build patient lists.
    # Active Patients: 3 random patients whose MedicalRecord.address matches this clinic (city or full address).
    try:
        matching_patient_ids = list(MedicalRecord.objects.filter(
            Q(address__icontains=clinic.city) | Q(address__iexact=clinic.full_address)
        ).values_list('patient_id', flat=True).distinct())
    except Exception:
        matching_patient_ids = []

    if matching_patient_ids:
        active_patients = list(Patient.objects.filter(id__in=matching_patient_ids).order_by('?')[:3])
    else:
        active_patients = []

    # Community Members: 3 random patients who had an accepted/confirmed booking with this clinic.
    try:
        booked_patient_ids = list(Appointment.objects.filter(clinic=clinic, status='confirmed').values_list('patient_id', flat=True).distinct())
    except Exception:
        booked_patient_ids = []

    if booked_patient_ids:
        community_patients = list(Patient.objects.filter(id__in=booked_patient_ids).order_by('?')[:3])
    else:
        community_patients = []
    pending_requests = assigned_patients.filter(status='pending').count()
    # ===== Community patients: show up to 3 most-recent distinct patients with CONFIRMED appointments =====
    community_patients = community_patients[:3]
    post_error = None
    if request.method == 'POST' and 'post_content' in request.POST:
        description = request.POST.get('post_content', '').strip()
        image = request.FILES.get('post_image')
        video = request.FILES.get('post_video')
        if description:
            post = Post.objects.create(
                clinic=clinic,
                author=request.user,
                description=description,
                image=image if image else None,
                video=video if video else None
            )
            messages.success(request, 'Post created successfully!')
            return redirect('clinic_dashboard')
        else:
            post_error = 'Please write something to post.'
    # Show all posts site-wide in the clinic dashboard 'All Posts' section
    posts = Post.objects.all().order_by('-created_at')
    # Posts authored by the clinic user (ensure we show only posts from this clinic account)
    clinic_posts = Post.objects.filter(author=clinic.user).order_by('-created_at')
    my_posts = posts.filter(author=request.user)
    if request.method == 'POST' and 'image' in request.FILES:
        gallery_form = ClinicGalleryForm(request.POST, request.FILES)
        if gallery_form.is_valid():
            gallery_item = gallery_form.save(commit=False)
            gallery_item.clinic = clinic
            gallery_item.save()
            messages.success(request, 'Image added to gallery!')
            return redirect('clinic_dashboard')
    if request.method == 'POST' and 'service_name' in request.POST:
        service_form = ClinicServiceForm(request.POST)
        if service_form.is_valid():
            service = service_form.save(commit=False)
            service.clinic = clinic
            service.save()
            messages.success(request, 'Service added!')
            return redirect('clinic_dashboard')
    gallery_form = ClinicGalleryForm()
    service_form = ClinicServiceForm()
    gallery_images = ClinicGallery.objects.filter(clinic=clinic)
    services = ClinicService.objects.filter(clinic=clinic)
    # Reviews summary for sidebar rating
    try:
        reviews = Review.objects.filter(clinic=clinic)
        reviews_count = reviews.count()
        avg_rating = reviews.aggregate(avg=Avg('rating'))['avg']
        if reviews_count == 0:
            display_rating = 3.0
        else:
            display_rating = round(avg_rating, 1) if avg_rating is not None else 3.0
    except Exception:
        reviews_count = 0
        display_rating = 3.0
    context = {
        'clinic': clinic,
        'assigned_patients': assigned_patients,
        'assigned_patients_unique': assigned_patients_unique,
        'total_patients': total_patients,
        'active_patients': active_patients,
        'pending_requests': pending_requests,
        'total_appointments': total_appointments,
        'pending_appointments': pending_appointments,
        'confirmed_appointments': confirmed_appointments,
        'recent_appointments': recent_appointments,
        'gallery_form': gallery_form,
        'service_form': service_form,
        'gallery_images': gallery_images,
        'services': services,
        'display_rating': display_rating,
        'reviews_count': reviews_count,
        'posts': posts,
        'clinic_posts': clinic_posts,
        'my_posts': my_posts,
        'post_error': post_error,
        'community_patients': community_patients,
    }
    return render(request, 'clinics/clinic_dashboard.html', context)
# Clinic signup view (restored)
def clinic_signup_view(request):
    if request.method == 'POST':
        form = ClinicSignUpForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                user = form.save()
                login(request, user)
                messages.success(request, 'Clinic account created successfully! Your profile is now live.')
                return redirect('clinic_dashboard')
            except Exception as e:
                messages.error(request, f'An error occurred during registration: {str(e)}')
        else:
            for field_name, errors in form.errors.items():
                for error in errors:
                    if field_name == '__all__':
                        messages.error(request, f"Error: {error}")
                    else:
                        field_label = form.fields[field_name].label if field_name in form.fields else field_name
                        messages.error(request, f"{field_label}: {error}")
    else:
        form = ClinicSignUpForm()
    context = {
        'form': form,
        'title': 'Clinic Registration'
    }
    return render(request, 'clinics/signup.html', context)
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth import login
from django.core.files.storage import FileSystemStorage
import os
from accounts.forms import UserCreationForm
from patients.models import Patient, MedicalRecord
from .forms import AppointmentForm, ClinicSignUpForm, ClinicGalleryForm, ClinicServiceForm, ClinicUpdateForm
from .models import Appointment, Clinic, ClinicGallery, ClinicService
from posts.models import Post, Comment

def clinic_detail_view(request, clinic_id):
    # Forced error removed. Now ensure all context variables are set and print context for debugging.
    from django.conf import settings
    import os
    db_path = settings.DATABASES['default'].get('NAME', '(no db name)')
    abs_db_path = os.path.abspath(db_path) if db_path else '(empty)'
    cwd = os.getcwd()
    settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', '(not set)')
    logger.debug("Entered clinic_detail_view for clinic_id=%s, method=%s; DB=%s; SETTINGS=%s", clinic_id, request.method, abs_db_path, settings_module)
    clinic = get_object_or_404(Clinic, id=clinic_id)
    # Build context using helper to allow alternate views
    def _build_context(request, clinic):
        gallery_images = ClinicGallery.objects.filter(clinic=clinic)
        services = ClinicService.objects.filter(clinic=clinic)
        # Include posts that are either linked to this clinic or authored by the clinic user
        posts = Post.objects.filter(Q(clinic=clinic) | Q(author=clinic.user)).order_by('-created_at')
        # Only posts authored by this clinic's user
        clinic_posts = Post.objects.filter(author=clinic.user).order_by('-created_at')
        reviews = Review.objects.filter(clinic=clinic).select_related('patient').order_by('-created_at')
        avg_rating = reviews.aggregate(avg=Avg('rating'))['avg']
        if avg_rating is not None:
            avg_rating = round(avg_rating, 1)
        else:
            avg_rating = None

        # Rating to display: if no reviews, default to 3.0
        reviews_count = reviews.count()
        if reviews_count == 0:
            display_rating = 3.0
        else:
            display_rating = avg_rating if avg_rating is not None else 3.0

        patient = None
        is_connected = False
        connection_status = None
        review_error = None
        if request.user.is_authenticated:
            try:
                patient = Patient.objects.get(user=request.user)
                if request.user.user_type == 'patient':
                    active_connection = Appointment.objects.filter(clinic=clinic, patient=patient, status='active').exists()
                    pending_connection = Appointment.objects.filter(clinic=clinic, patient=patient, status='pending').exists()
                    if active_connection:
                        is_connected = True
                        connection_status = 'active'
                    elif pending_connection:
                        is_connected = True
                        connection_status = 'pending'
            except Patient.DoesNotExist:
                logger.warning("[DEBUG] Patient.DoesNotExist for user %s", request.user)
                patient = None

        facilities_list = [f.strip() for f in clinic.facilities.split(',')] if clinic.facilities else []
        # Build acceptance fields list for the template: pairs (field_name, human_label)
        acceptance_fields = []
        try:
            for field in clinic._meta.fields:
                if field.name.startswith('accepts_'):
                    try:
                        accepted = getattr(clinic, field.name)
                    except Exception:
                        accepted = False
                    if accepted:
                        label = field.help_text if getattr(field, 'help_text', None) else str(field.verbose_name).replace('_', ' ').title()
                        acceptance_fields.append((field.name, label))
        except Exception:
            acceptance_fields = []
        context = {
            'clinic': clinic,
            'gallery_images': gallery_images,
            'services': services,
            'is_connected': is_connected,
            'connection_status': connection_status,
            'patient': patient,
            'facilities_list': facilities_list,
            'acceptance_fields': acceptance_fields,
            'posts': posts,
            'clinic_posts': clinic_posts,
            'reviews': reviews,
            'avg_rating': avg_rating,
            'display_rating': display_rating,
            'reviews_count': reviews_count,
            'review_error': review_error,
            'db_path': abs_db_path,
            'cwd': cwd,
            'settings_module': settings_module,
            'clinic_detail_marker': 'CLINIC_DETAIL_VIEW_ACTIVE',
        }
        return context

    context = _build_context(request, clinic)
    # Render the patient-facing clinic detail template (not the clinic-only view)
    return render(request, 'clinics/clinic_detail.html', context)


def clinic_detail_clinic_view(request, clinic_id):
    """Clinic-facing detail view without booking UI."""
    clinic = get_object_or_404(Clinic, id=clinic_id)
    # provide same debug vars used by the main view/template
    from django.conf import settings
    db_path = settings.DATABASES['default'].get('NAME', '(no db name)')
    abs_db_path = os.path.abspath(db_path) if db_path else '(empty)'
    cwd = os.getcwd()
    settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', '(not set)')
    # reuse builder above
    def _build_context(request, clinic):
        gallery_images = ClinicGallery.objects.filter(clinic=clinic)
        services = ClinicService.objects.filter(clinic=clinic)
        # Include posts that are either linked to this clinic or authored by the clinic user
        posts = Post.objects.filter(Q(clinic=clinic) | Q(author=clinic.user)).order_by('-created_at')
        clinic_posts = Post.objects.filter(author=clinic.user).order_by('-created_at')
        reviews = Review.objects.filter(clinic=clinic).select_related('patient').order_by('-created_at')
        avg_rating = reviews.aggregate(avg=Avg('rating'))['avg']
        if avg_rating is not None:
            avg_rating = round(avg_rating, 1)
        else:
            avg_rating = None
        reviews_count = reviews.count()
        if reviews_count == 0:
            display_rating = 3.0
        else:
            display_rating = avg_rating if avg_rating is not None else 3.0
        patient = None
        is_connected = False
        connection_status = None
        review_error = None
        if request.user.is_authenticated:
            try:
                patient = Patient.objects.get(user=request.user)
                if request.user.user_type == 'patient':
                    active_connection = Appointment.objects.filter(clinic=clinic, patient=patient, status='active').exists()
                    pending_connection = Appointment.objects.filter(clinic=clinic, patient=patient, status='pending').exists()
                    if active_connection:
                        is_connected = True
                        connection_status = 'active'
                    elif pending_connection:
                        is_connected = True
                        connection_status = 'pending'
            except Patient.DoesNotExist:
                patient = None
        facilities_list = [f.strip() for f in clinic.facilities.split(',')] if clinic.facilities else []
        acceptance_fields = []
        try:
            for field in clinic._meta.fields:
                if field.name.startswith('accepts_'):
                    try:
                        accepted = getattr(clinic, field.name)
                    except Exception:
                        accepted = False
                    if accepted:
                        label = field.help_text if getattr(field, 'help_text', None) else str(field.verbose_name).replace('_', ' ').title()
                        acceptance_fields.append((field.name, label))
        except Exception:
            acceptance_fields = []
        context = {
            'clinic': clinic,
            'gallery_images': gallery_images,
            'services': services,
            'is_connected': is_connected,
            'connection_status': connection_status,
            'patient': patient,
            'facilities_list': facilities_list,
            'acceptance_fields': acceptance_fields,
            'posts': posts,
            'clinic_posts': clinic_posts,
            'reviews': reviews,
            'avg_rating': avg_rating,
            'display_rating': display_rating,
            'reviews_count': reviews_count,
            'review_error': review_error,
            'db_path': abs_db_path,
            'cwd': cwd,
            'settings_module': settings_module,
            'clinic_detail_marker': 'CLINIC_DETAIL_CLINIC_VIEW',
            'omit_booking': True,
        }
        return context

    context = _build_context(request, clinic)
    # Add current clinic (the logged-in clinic user) and unread count for header badges
    current_clinic = None
    total_unread = 0
    if request.user.is_authenticated and getattr(request.user, 'user_type', None) == 'clinic':
        try:
            current_clinic = Clinic.objects.get(user=request.user)
        except Clinic.DoesNotExist:
            current_clinic = None
        # compute unread messages for header badge
        try:
            from chat.models import ChatRoom, Message
            chat_rooms = ChatRoom.objects.filter(Q(user1=request.user) | Q(user2=request.user))
            total_unread = Message.objects.filter(chat_room__in=chat_rooms, is_read=False).exclude(sender=request.user).count()
        except Exception:
            total_unread = 0

    context.update({
        'current_clinic': current_clinic,
        'total_unread': total_unread,
    })

    return render(request, 'clinics/clinic_datils_clinic.html', context)
    

@login_required
def clinic_ping(request):
    """Simple endpoint for clinics to refresh their `last_seen` timestamp."""
    try:
        if hasattr(request.user, 'clinic'):
            from django.utils import timezone
            request.user.clinic.last_seen = timezone.now()
            request.user.clinic.save(update_fields=['last_seen'])
            return JsonResponse({'ok': True})
    except Exception:
        pass
    return JsonResponse({'ok': False}, status=400)


@login_required
def clinic_settings_view(request):
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')

    clinic = get_object_or_404(Clinic, user=request.user)

    if request.method == 'POST':
        form = ClinicUpdateForm(request.POST, request.FILES, instance=clinic)
        if form.is_valid():
            form.save()
            messages.success(request, 'Clinic settings updated successfully!')
            return redirect('clinic_settings')
    else:
        form = ClinicUpdateForm(instance=clinic)

    context = {
        'clinic': clinic,
        'form': form,
    }
    return render(request, 'clinics/settings.html', context)



@login_required
def manage_gallery_view(request):
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    clinic = get_object_or_404(Clinic, user=request.user)
    
    if request.method == 'POST':
        form = ClinicGalleryForm(request.POST, request.FILES)
        if form.is_valid():
            gallery_item = form.save(commit=False)
            gallery_item.clinic = clinic
            gallery_item.save()
            messages.success(request, 'Image added to gallery!')
            return redirect('manage_gallery')
    else:
        form = ClinicGalleryForm()
    
    gallery_images = ClinicGallery.objects.filter(clinic=clinic)
    
    context = {
        'clinic': clinic,
        'form': form,
        'gallery_images': gallery_images,
    }
    return render(request, 'clinics/manage_gallery.html', context)

@login_required
def delete_gallery_image_view(request, image_id):
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    clinic = get_object_or_404(Clinic, user=request.user)
    image = get_object_or_404(ClinicGallery, id=image_id, clinic=clinic)
    
    if request.method == 'POST':
        image.delete()
        messages.success(request, 'Image deleted successfully!')
    
    return redirect('manage_gallery')


def patient_detail_view(request, patient_id):
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    clinic = get_object_or_404(Clinic, user=request.user)
    patient = get_object_or_404(Patient, id=patient_id)

    assignment = get_object_or_404(Appointment, clinic=clinic, patient=patient)

    try:
        medical_record = MedicalRecord.objects.get(patient=patient)
    except MedicalRecord.DoesNotExist:
        medical_record = None
    
    if request.method == 'POST':
        form = AppointmentForm(request.POST, instance=assignment, clinic=clinic, patient=assignment.patient)
        if form.is_valid():
            form.save()
            messages.success(request, 'Patient information updated successfully!')
            return redirect('patient_detail', patient_id=patient.id)
    else:
        form = AppointmentForm(instance=assignment, clinic=clinic, patient=assignment.patient)
    
    context = {
        'patient': patient,
        'medical_record': medical_record,
        'assignment': assignment,
        'form': form,
        'clinic': clinic,
    }
    return render(request, 'clinics/patient_detail.html', context)

@login_required
def search_patients_view(request):
    # Allow both clinics and patients to access this search. Clinics get clinic-specific behavior.
    if request.user.user_type not in ('clinic', 'patient'):
        messages.error(request, 'Access denied.')
        return redirect('login')

    clinic = None
    if request.user.user_type == 'clinic':
        clinic = get_object_or_404(Clinic, user=request.user)

    query = request.GET.get('q', '') or ''
    query = query.strip()

    patients = []
    assigned_patients = None

    # If the current user is a clinic, provide their assigned patients for the empty state
    if clinic is not None:
        assigned_patients = Appointment.objects.filter(clinic=clinic).select_related('patient')

    if query:
        # support multi-token name searches (e.g., first + last)
        tokens = [t for t in query.split() if t]
        patients_qs = Patient.objects.all()

        # build OR queries for tokens across several fields
        q_obj = Q()
        for t in tokens:
            q_obj |= Q(full_name__icontains=t)
            q_obj |= Q(phone__icontains=t)
            q_obj |= Q(user__email__icontains=t)
            q_obj |= Q(user__username__icontains=t)

        patients_qs = patients_qs.filter(q_obj).order_by('full_name')

        # If a clinic is searching, exclude patients already linked to this clinic
        if clinic is not None:
            patients_qs = patients_qs.exclude(appointment__clinic=clinic)

        patients = patients_qs.distinct()[:50]

    context = {
        'patients': patients,
        'query': query,
        'clinic': clinic,
        'assigned_patients': assigned_patients,
    }
    return render(request, 'clinics/search_patients.html', context)


@login_required
def search_patient_clinic_page(request):
    """Render the full-page clinic patient search UI (simple wrapper around the AJAX partial).
    """
    if request.user.user_type != 'clinic':
        return redirect('login')
    clinic = get_object_or_404(Clinic, user=request.user)
    context = {'clinic': clinic}
    return render(request, 'clinics/search_patient_clinic.html', context)

@login_required
def assign_patient_view(request, patient_id):
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    clinic = get_object_or_404(Clinic, user=request.user)
    patient = get_object_or_404(Patient, id=patient_id)
    
    if Appointment.objects.filter(clinic=clinic, patient=patient).exists():
        messages.warning(request, 'This patient is already assigned to your clinic.')
        return redirect('clinic_dashboard')
    
    Appointment.objects.create(
        clinic=clinic,
        patient=patient,
        notes=f"Assigned on {request.user.date_joined.strftime('%Y-%m-%d')}"
    )
    
    messages.success(request, f'Patient {patient.full_name} has been assigned to your clinic!')
    return redirect('clinic_dashboard')



@login_required
def create_appointment_view(request, clinic_id):
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    clinic = get_object_or_404(Clinic, id=clinic_id)
    patient = get_object_or_404(Patient, user=request.user)
    
    medical_records = MedicalRecord.objects.filter(patient=patient)
    if not medical_records.exists():
        messages.error(request, 'You need to create a medical record before booking an appointment.')
        return redirect('medical_record_create')
    
    if request.method == 'POST':
        form = AppointmentForm(request.POST, patient=patient, clinic=clinic)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.patient = patient
            appointment.clinic = clinic
            appointment.save()
            
            messages.success(request, 'Appointment request sent successfully! The clinic will review your booking.')
            return redirect('patient_appointments')
    else:
        form = AppointmentForm(patient=patient, clinic=clinic)
        # Set default date to tomorrow
        form.initial['appointment_date'] = date.today()
    
    context = {
        'form': form,
        'clinic': clinic,
        'patient': patient,
    }
    return render(request, 'clinics/create_appointment.html', context)

@login_required
def patient_appointments_view(request):
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    patient = get_object_or_404(Patient, user=request.user)
    appointments = Appointment.objects.filter(patient=patient).select_related('clinic', 'medical_record')
    # compute total_unread for header/sidebar badges
    from chat.models import ChatRoom, Message
    chat_rooms = ChatRoom.objects.filter(Q(user1=request.user) | Q(user2=request.user))
    total_unread = Message.objects.filter(chat_room__in=chat_rooms, is_read=False).exclude(sender=request.user).count()

    context = {
        'appointments': appointments,
        'patient': patient,
        'total_unread': total_unread,
    }
    return render(request, 'patient/appointments.html', context)

@login_required
def clinic_appointments_view(request):
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    clinic = get_object_or_404(Clinic, user=request.user)
    appointments = Appointment.objects.filter(clinic=clinic).select_related('patient', 'medical_record')
    
    status_filter = request.GET.get('status', '')
    if status_filter:
        appointments = appointments.filter(status=status_filter)
    
    total_appointments = Appointment.objects.filter(clinic=clinic).count()
    pending_appointments = Appointment.objects.filter(clinic=clinic, status='pending').count()
    confirmed_appointments = Appointment.objects.filter(clinic=clinic, status='confirmed').count()
    from datetime import date
    upcoming_appointments = Appointment.objects.filter(
        clinic=clinic, 
        status='confirmed', 
        appointment_date__gte=date.today()
    ).count()
    
    context = {
        'appointments': appointments,
        'clinic': clinic,
        'status_filter': status_filter,
        'total_appointments': total_appointments,
        'pending_appointments': pending_appointments,
        'confirmed_appointments': confirmed_appointments,
        'upcoming_appointments': upcoming_appointments,
    }
    return render(request, 'clinics/clinic_appointments.html', context)

@login_required
def update_appointment_status_view(request, appointment_id):
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    clinic = get_object_or_404(Clinic, user=request.user)
    appointment = get_object_or_404(Appointment, id=appointment_id, clinic=clinic)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Appointment.STATUS_CHOICES):
            appointment.status = new_status
            appointment.save()
            messages.success(request, f'Appointment status updated to {new_status}.')
        else:
            messages.error(request, 'Invalid status.')
    
    return redirect('clinic_appointments')


@login_required
def update_appointment_view(request, appointment_id):
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    clinic = get_object_or_404(Clinic, user=request.user)
    appointment = get_object_or_404(Appointment, id=appointment_id, clinic=clinic)
    
    if request.method == 'POST':
        form = AppointmentForm(request.POST, instance=appointment, clinic=clinic, patient=appointment.patient)
        if form.is_valid():
            form.save()
            messages.success(request, 'Appointment updated successfully!')
            return redirect('clinic_appointments')
    else:
        form = AppointmentForm(instance=appointment, clinic=clinic, patient=appointment.patient)
    
    context = {
        'form': form,
        'appointment': appointment,
        'clinic': clinic,
    }
    return render(request, 'clinics/edit_appointment.html', context)


@login_required
def clinic_my_posts_view(request):
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')

    clinic = get_object_or_404(Clinic, user=request.user)
    # posts authored by this clinic user
    my_posts = Post.objects.filter(clinic=clinic, author=request.user).order_by('-created_at')

    context = {
        'clinic': clinic,
        'my_posts': my_posts,
    }
    return render(request, 'clinics/clinic_my_posts.html', context)


@login_required
@require_POST
def delete_post_view(request, post_id):
    from posts.models import Post
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')

    clinic = get_object_or_404(Clinic, user=request.user)
    post = get_object_or_404(Post, id=post_id, clinic=clinic)

    # Only allow deletion if the requesting user is the author
    if post.author != request.user:
        messages.error(request, 'You do not have permission to delete this post.')
        return redirect('clinic_my_posts')

    post.delete()
    messages.success(request, 'Post deleted successfully.')
    return redirect('clinic_my_posts')
