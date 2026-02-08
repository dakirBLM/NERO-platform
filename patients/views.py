from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.http import HttpResponseForbidden, HttpResponse, Http404, FileResponse
from clinics.models import Appointment
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
import mimetypes
import os
import io
import logging
from cryptography.fernet import InvalidToken

logger = logging.getLogger(__name__)

# Delete appointment view
@login_required
@require_POST
def delete_appointment_view(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    # Only allow the patient who owns the appointment to delete
    if appointment.patient.user != request.user:
        return HttpResponseForbidden("You do not have permission to delete this appointment.")
    appointment.delete()
    messages.success(request, "Appointment deleted successfully.")
    return redirect('patient_appointments')
from accounts.forms import PatientSignUpForm
from .forms import PatientForm, MedicalRecordForm
from .models import Patient, MedicalRecord
from django.db.models import Q
from clinics.models import Appointment, Clinic, ClinicService
from django.core.paginator import Paginator
import random

def patient_signup_view(request):
    if request.method == 'POST':
        user_form = PatientSignUpForm(request.POST, request.FILES)
        if user_form.is_valid():
            user = user_form.save()
            login(request, user)
            messages.success(request, 'Account created successfully! Your dashboard is ready.')
            return redirect('patient_dashboard')
    else:
        user_form = PatientSignUpForm()
    return render(request, 'patient/signup.html', {'form': user_form})

@login_required
def medical_record_create_view(request):
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('login')
    patient, _ = Patient.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        medical_form = MedicalRecordForm(request.POST, request.FILES)
        
        if  medical_form.is_valid():
            medical_record = medical_form.save(commit=False)
            medical_record.patient = patient
            medical_record.save()
            
            messages.success(request, 'Medical record created successfully!')
            return redirect('medical_record_success')
        else:
            print(medical_form.errors)
    else:
        medical_form = MedicalRecordForm()

    # Ensure patient form is always available to the template (so `patient` and its avatar can render)
    patient_form = PatientForm(instance=patient)
    context = {
        'patient_form': patient_form,
        'medical_form': medical_form,
        'patient': patient,
    }
    return render(request, 'patient/medical_record_form.html', context)

@login_required
def medical_record_success_view(request):
    try:
        patient = Patient.objects.get(user=request.user)
        has_records = MedicalRecord.objects.filter(patient=patient).exists()
    except Patient.DoesNotExist:
        has_records = False
    # Provide patient and latest medical record so template can show avatar and summary
    medical_record = None
    is_update = request.GET.get('update', '0') == '1'
    try:
        if has_records:
            medical_record = MedicalRecord.objects.filter(patient=patient).order_by('-updated_at').first()
    except Exception:
        medical_record = None

    context = {
        'has_records': has_records,
        'patient': patient if 'patient' in locals() else None,
        'medical_record': medical_record,
        'is_update': is_update,
    }
    return render(request, 'patient/medical_record_success.html', context)

@login_required
def patient_dashboard_view(request):
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('login')
    from clinics.models import Clinic
    try:
        patient = Patient.objects.get(user=request.user)
    except Patient.DoesNotExist:
        patient = None
    medical_records = MedicalRecord.objects.filter(patient=patient).order_by('-created_at')

    upcoming_appointments = 0
    pending_appointments = 0
    recent_appointments = None
    suggested_clinics = []
    active_patients = []

    if medical_records.exists():
        from datetime import date
        appointments = Appointment.objects.filter(patient=patient)
        upcoming_appointments = appointments.filter(
            status='confirmed',
            appointment_date__gte=date.today()
        ).count()
        pending_appointments = appointments.filter(status='pending').count()
        recent_appointments = appointments.select_related('clinic').order_by('-created_at')[:3]

        # Get the most recent medical record
        last_record = medical_records.first()
        # Try to match by address (city or region info). Prioritize clinics
        # whose `city` or `address` contains the patient's city (exact match first),
        # then fill remaining slots with other clinics (randomized).
        # Build scored recommendations based on multiple signals from the medical record
        # Weights (tunable): reviews 40%, city/address 30%, service 15%, acceptance 15%
        REVIEW_W = 0.40
        CITY_W = 0.30
        SERVICE_W = 0.15
        ACCEPT_W = 0.15

        # Extract city token from medical record address
        addr = (last_record.address or '').strip()
        city_candidate = addr.split(',')[0].strip().lower() if addr else ''

        # Patient's requested service (optional)
        desired_service = (last_record.main_diagnosis or '').strip().lower()

        from reviews.models import Review

        clinics_qs = Clinic.objects.all()
        scored = []
        for clinic in clinics_qs:
            # Review score: average rating normalized to [0,1]
            try:
                rv = Review.objects.filter(clinic=clinic).aggregate(avg=models.Avg('rating'))['avg']
            except Exception:
                rv = None
            review_score = (rv / 5.0) if rv else 0.0

            # City/address match score
            city_score = 0.0
            if city_candidate:
                if clinic.city and city_candidate == clinic.city.strip().lower():
                    city_score = 1.0
                elif city_candidate in (clinic.address or '').lower():
                    city_score = 0.6
                elif city_candidate in (clinic.city or '').lower():
                    city_score = 0.8

            # Service match score (check clinic services and specialization)
            service_score = 0.0
            if desired_service:
                try:
                    svc_match = clinic.services.filter(service_name__icontains=desired_service).exists()
                except Exception:
                    svc_match = False
                if svc_match:
                    service_score = 1.0
                elif desired_service in (clinic.specialization or '').lower() or desired_service in (clinic.other_specializations or '').lower():
                    service_score = 0.7

            # Acceptance score: ensure clinic accepts the patient's special conditions
            # Map medical record boolean fields to clinic acceptance fields
            condition_map = [
                ('uses_wheelchair', 'accepts_wheelchair'),
                ('uses_walker', 'accepts_walker'),
                ('uses_crutch', 'accepts_crutch'),
                ('uses_electric_wheelchair', 'accepts_electric_wheelchair'),
                ('has_bedsores', 'accepts_bedsores'),
                ('has_diabetes', 'accepts_diabetes'),
                ('uses_insulin', 'accepts_insulin'),
                ('has_heart_problems', 'accepts_heart_problems'),
                ('has_high_blood_pressure', 'accepts_high_blood_pressure'),
                ('has_infectious_diseases', 'accepts_infectious_diseases'),
                ('has_vein_thrombosis', 'accepts_vein_thrombosis'),
                ('has_depression', 'accepts_depression'),
                ('uses_permanent_catheter', 'accepts_catheter'),
                ('uses_intermittent_catheter', 'accepts_catheter'),
                ('uses_medical_condom', 'accepts_medical_condom'),
                ('uses_diapers', 'accepts_diapers'),
            ]
            required_conditions = 0
            accepts_ok = 0
            for mr_field, clinic_field in condition_map:
                try:
                    if getattr(last_record, mr_field, False):
                        required_conditions += 1
                        if getattr(clinic, clinic_field, False):
                            accepts_ok += 1
                except Exception:
                    continue

            if required_conditions == 0:
                acceptance_score = 1.0
            else:
                acceptance_score = accepts_ok / required_conditions

            # Final weighted score
            final_score = (REVIEW_W * review_score) + (CITY_W * city_score) + (SERVICE_W * service_score) + (ACCEPT_W * acceptance_score)

            scored.append((final_score, review_score, clinic))

        # Sort by final score desc, then by review_score desc
        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        suggested_clinics = [c for _, _, c in scored][:3]

    # --- Active Community Members: 3 random online patients we've chatted with ---
    from chat.models import ChatRoom, Message
    from accounts.models import User
    # Find all chat rooms involving this user
    chat_rooms = ChatRoom.objects.filter(Q(user1=request.user) | Q(user2=request.user))
    # compute total unread across all chat rooms for this user
    total_unread = Message.objects.filter(chat_room__in=chat_rooms, is_read=False).exclude(sender=request.user).count()
    # Find all unique patient users we've chatted with (excluding self)
    patient_user_ids = set()
    for room in chat_rooms:
        other = room.user2 if room.user1 == request.user else room.user1
        # Only include if other is a patient
        try:
            patient_obj = Patient.objects.get(user=other)
            patient_user_ids.add(patient_obj.id)
        except Patient.DoesNotExist:
            continue
    # Simulate online status: patients with a message in the last 5 minutes
    from django.utils import timezone
    from datetime import timedelta
    now = timezone.now()
    online_patients = []
    for pid in patient_user_ids:
        user = Patient.objects.get(id=pid).user
        recent_msg = Message.objects.filter(sender=user, timestamp__gte=now-timedelta(minutes=5)).exists()
        if recent_msg:
            online_patients.append(Patient.objects.get(id=pid))
    random.shuffle(online_patients)
    active_patients = online_patients[:3]

    # Fallback: last 3 people we've chatted with, ordered by most recent message
    last_chatted_patients = []
    if not active_patients:
        # Get all messages sent or received by the user, order by timestamp desc
        chat_messages = Message.objects.filter(
            chat_room__in=chat_rooms
        ).exclude(sender=request.user).order_by('-timestamp')
        seen_patient_ids = set()
        for msg in chat_messages:
            try:
                patient_obj = Patient.objects.get(user=msg.sender)
                if patient_obj.id not in seen_patient_ids:
                    last_chatted_patients.append(patient_obj)
                    seen_patient_ids.add(patient_obj.id)
                if len(last_chatted_patients) >= 3:
                    break
            except Patient.DoesNotExist:
                continue

    # --- Post Creation ---
    from posts.models import Post
    from clinics.models import Clinic
    post_error = None
    if request.method == 'POST' and 'post_content' in request.POST:
        description = request.POST.get('post_content', '').strip()
        image = request.FILES.get('post_image')
        video = request.FILES.get('post_video')
        # For patient, let them pick a clinic or assign to first clinic (or null)
        clinic = Clinic.objects.first() if Clinic.objects.exists() else None
        if description and clinic:
            Post.objects.create(
                clinic=clinic,
                author=request.user,
                description=description,
                image=image if image else None,
                video=video if video else None
            )
            messages.success(request, 'Post created successfully!')
            return redirect('patient_dashboard')
        else:
            post_error = 'Please write something to post.'

    posts = Post.objects.all().order_by('-created_at')
    my_posts = posts.filter(author=request.user)

    return render(request, 'patient/dashboard/patient_dashboard.html', {
        'patient': patient,
        'medical_records': medical_records,
        'upcoming_appointments': upcoming_appointments,
        'pending_appointments': pending_appointments,
        'recent_appointments': recent_appointments,
        'suggested_clinics': suggested_clinics,
        'active_patients': active_patients,
        'last_chatted_patients': last_chatted_patients,
        'posts': posts,
        'my_posts': my_posts,
        'post_error': post_error,
        'total_unread': total_unread,
    })


@login_required
def patient_my_posts_view(request):
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('login')
    from posts.models import Post
    try:
        patient = Patient.objects.get(user=request.user)
    except Patient.DoesNotExist:
        patient = None
    my_posts = Post.objects.filter(author=request.user).order_by('-created_at')
    # compute total_unread for header/sidebar badges
    from chat.models import ChatRoom, Message
    chat_rooms = ChatRoom.objects.filter(Q(user1=request.user) | Q(user2=request.user))
    total_unread = Message.objects.filter(chat_room__in=chat_rooms, is_read=False).exclude(sender=request.user).count()

    return render(request, 'patient/dashboard/my_posts.html', {
        'patient': patient,
        'my_posts': my_posts,
        'total_unread': total_unread,
    })


@login_required
@require_POST
def delete_my_post_view(request, post_id):
    from posts.models import Post
    post = get_object_or_404(Post, id=post_id)
    if post.author != request.user:
        return HttpResponseForbidden("You do not have permission to delete this post.")
    post.delete()
    messages.success(request, 'Post deleted successfully.')
    return redirect('patient_my_posts')

@login_required
def patient_medical_records_view(request):
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('login')

    try:
        patient = Patient.objects.get(user=request.user)
    except Patient.DoesNotExist:
        patient = None

    medical_records = MedicalRecord.objects.filter(patient=patient).order_by('-created_at')

    context = {
        'patient': patient,
        'medical_records': medical_records,
    }
    return render(request, 'patient/medical_records.html', context)
    
@login_required
def see_medical_record_view(request, record_id=None):   
    

        
    if record_id:
        medical_record = get_object_or_404(MedicalRecord, id=record_id)
        context = {
            'medical_record': medical_record,
            'single_record': True
        }
        if hasattr(request.user, 'user_type') and request.user.user_type == 'clinic':
            return render(request, 'clinics/see_medical_record_clinic.html', context)
        else:
            return render(request, 'patient/see_medical_record.html', context)


@login_required
def secure_medical_report_download(request, record_id):
    """Return decrypted medical report using storage.open()."""
    medical_record = get_object_or_404(MedicalRecord, id=record_id)

    # Permission: owner patient, clinic users, or staff
    if not (
        request.user == medical_record.patient.user
        or getattr(request.user, 'user_type', None) == 'clinic'
        or request.user.is_staff
    ):
        return HttpResponseForbidden('You do not have permission to access this file.')

    if not medical_record.medical_reports:
        raise Http404('No medical report attached to this record.')

    # Open via storage to get decrypted bytes and stream via FileResponse
    try:
        f = medical_record.medical_reports.open('rb')
        data = f.read()
    except InvalidToken:
        logger.exception('Failed to decrypt medical report for record %s', record_id)
        return HttpResponse('Failed to decrypt file. Check server encryption settings.', status=500)
    except Exception:
        logger.exception('Error reading medical report for record %s', record_id)
        return HttpResponse('Failed to read file from storage.', status=500)
    finally:
        try:
            f.close()
        except Exception:
            pass

    filename = os.path.basename(medical_record.medical_reports.name)
    content_type, _ = mimetypes.guess_type(filename)
    if not content_type:
        content_type = 'application/octet-stream'

    buffer = io.BytesIO(data)
    response = FileResponse(buffer, content_type=content_type)
    response['Content-Length'] = str(len(data))
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def secure_movement_video_view(request, record_id):
    """Return decrypted movement video (inline) using storage.open()."""
    medical_record = get_object_or_404(MedicalRecord, id=record_id)

    if not (
        request.user == medical_record.patient.user
        or getattr(request.user, 'user_type', None) == 'clinic'
        or request.user.is_staff
    ):
        return HttpResponseForbidden('You do not have permission to access this file.')

    if not medical_record.patient_movement_video:
        raise Http404('No movement video attached to this record.')

    try:
        f = medical_record.patient_movement_video.open('rb')
        data = f.read()
    except InvalidToken:
        logger.exception('Failed to decrypt movement video for record %s', record_id)
        return HttpResponse('Failed to decrypt video. Check server encryption settings.', status=500)
    except Exception:
        logger.exception('Error reading movement video for record %s', record_id)
        return HttpResponse('Failed to read video from storage.', status=500)
    finally:
        try:
            f.close()
        except Exception:
            pass

    filename = os.path.basename(medical_record.patient_movement_video.name)
    content_type, _ = mimetypes.guess_type(filename)
    if not content_type:
        content_type = 'video/mp4'

    buffer = io.BytesIO(data)
    response = FileResponse(buffer, content_type=content_type)
    response['Content-Length'] = str(len(data))
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response

    context = {
        'single_record': False
    }
    if hasattr(request.user, 'user_type') and request.user.user_type == 'clinic':
        return render(request, 'clinics/see_medical_record_clinic.html', context)
    else:
        return render(request, 'patient/see_medical_record.html', context)

def search_clinics_view(request):
    print("=== SEARCH CLINICS VIEW CALLED ===")
    query = request.GET.get('q', '')
    specialization = request.GET.get('specialization', 'all')
    city = request.GET.get('city', '')
    all_clinics = Clinic.objects.all()
    print(f"Total clinics in database: {all_clinics.count()}")
    for clinic in all_clinics:
        print(f"Clinic: {clinic.clinic_name}, City: {clinic.city}, Verified: {clinic.is_verified}")
    featured_clinics = None
    clinics_to_display = None
    if not query and specialization == 'all' and not city:
        print("Showing featured clinics (no search criteria)")
        clinic_list = list(all_clinics)
        if clinic_list:
            featured_clinics = random.sample(clinic_list, min(6, len(clinic_list)))
            print(f"Selected {len(featured_clinics)} featured clinics")
        else:
            print("No clinics available for featured section")
    else:
        print("Applying search filters")
        clinics = all_clinics
        if query:
            print(f"Applying query filter: {query}")
            clinics = clinics.filter(
                Q(clinic_name__icontains=query) |
                Q(description__icontains=query) |
                Q(tagline__icontains=query) |
                Q(specialization__icontains=query) |
                Q(other_specializations__icontains=query) |
                Q(city__icontains=query) |
                Q(state__icontains=query)
            ) 
        if specialization and specialization != 'all':
            print(f"Applying specialization filter: {specialization}")
            clinics = clinics.filter(specialization=specialization)
        
        if city:
            print(f"Applying city filter: {city}")
            clinics = clinics.filter(city__icontains=city)
        
        paginator = Paginator(clinics, 9)
        page_number = request.GET.get('page', 1)
        clinics_to_display = paginator.get_page(page_number)
        print(f"Search results: {clinics_to_display.object_list.count()} clinics")
    
    # Add patient to context for profile display
    patient = Patient.objects.get(user=request.user)
    context = {
        'clinics': clinics_to_display,
        'featured_clinics': featured_clinics,
        'query': query,
        'specialization': specialization,
        'city': city,
        'specialization_choices': Clinic.SPECIALIZATION_CHOICES,
        'patient': patient,
    }
    
    print(f"Sending to template - Featured: {featured_clinics is not None}, Search: {clinics_to_display is not None}")
    print("=== END SEARCH CLINICS VIEW ===")
    
    return render(request, 'patient/search_clinics.html', context)

@login_required
def medical_record_update_view(request, pk):
    record = get_object_or_404(MedicalRecord, pk=pk, patient=request.user.patient)
    if request.method == 'POST':
        form = MedicalRecordForm(request.POST, request.FILES, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, 'Medical record updated successfully!')
            return redirect('medical_record_success')
    else:
        form = MedicalRecordForm(instance=record)

    # Include patient and record in context so template can render profile info
    return render(request, 'patient/medical_record_form.html', {
        'medical_form': form,
        'patient': record.patient,
        'medical_record': record,
    })

@login_required
def medical_record_delete_view(request, pk):
    """Delete a medical record belonging to the current patient.

    Note: This view performs deletion immediately to align with the existing
    anchor link in the dashboard template. Consider changing the template to
    submit a POST request for safer semantics.
    """
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('login')

    record = get_object_or_404(MedicalRecord, pk=pk, patient=request.user.patient)
    record.delete()
    messages.success(request, 'Medical record deleted successfully.')
    return redirect('patient_dashboard')

@login_required
def patient_appointments_view(request):
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    try:
        patient = Patient.objects.get(user=request.user)
    except Patient.DoesNotExist:
        patient = None
    
    all_appointments = Appointment.objects.filter(patient=patient).select_related('clinic', 'medical_record').order_by('-appointment_date', '-created_at')

    status_filter = request.GET.get('status', '') or ''
    status_filter = status_filter.strip()
    print('DEBUG: raw status_filter =', status_filter)

    # Normalize and validate against model choices to avoid mismatch issues
    status_filter_normalized = status_filter.lower()
    allowed_statuses = [choice[0] for choice in Appointment.STATUS_CHOICES]

    if status_filter_normalized and status_filter_normalized in allowed_statuses:
        # Use case-insensitive match to be robust against stored casing
        appointments = all_appointments.filter(status__iexact=status_filter_normalized)
        status_filter = status_filter_normalized
        print('DEBUG: applying filter ->', status_filter)
        print('DEBUG: appointments queryset:', str(appointments.query))
    else:
        if status_filter and status_filter_normalized not in allowed_statuses:
            print('DEBUG: invalid status_filter provided, ignoring:', status_filter)
        appointments = all_appointments
        print('DEBUG: appointments queryset (no filter):', str(appointments.query))

    from datetime import date
    total_appointments = all_appointments.count()
    pending_appointments = all_appointments.filter(status='pending').count()
    confirmed_appointments = all_appointments.filter(status='confirmed').count()
    upcoming_appointments = all_appointments.filter(status='confirmed', appointment_date__gte=date.today()).count()

    context = {
        'patient': patient,
        'appointments': appointments,
        'status_filter': status_filter,
        'total_appointments': total_appointments,
        'pending_appointments': pending_appointments,
        'confirmed_appointments': confirmed_appointments,
        'upcoming_appointments': upcoming_appointments,
    }
    return render(request, 'patient/appointments.html', context)

@login_required
def cancel_appointment_view(request, appointment_id):
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    appointment = get_object_or_404(Appointment, id=appointment_id, patient=request.user.patient)
    
    if request.method == 'POST':
        appointment.status = 'cancelled'
        appointment.save()
        messages.success(request, 'Appointment cancelled successfully.')
    
    return redirect('patient_appointments')
