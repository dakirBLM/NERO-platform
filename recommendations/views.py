from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from . import utils as recommender_utils


@login_required
@require_http_methods(["GET"])
def questionnaire_view(request):
    """Render a simple questionnaire form for patients to answer."""
    # Get the current patient and their medical records
    from patients.models import Patient, MedicalRecord
    from clinics.models import ClinicService
    patient = None
    medical_records = []
    services = []
    if hasattr(request.user, 'user_type') and request.user.user_type == 'patient':
        try:
            patient = Patient.objects.get(user=request.user)
            medical_records = MedicalRecord.objects.filter(patient=patient)
        except Patient.DoesNotExist:
            pass
    # Get all unique service names
    services = ClinicService.objects.values_list('service_name', flat=True).distinct().order_by('service_name')
    return render(request, 'recommendations/questionnaire.html', {
        'medical_records': medical_records,
        'services': services,
        'patient': patient,
    })


@login_required
@require_http_methods(["POST"])
def recommendation_result_view(request):
    """Receive questionnaire POST and show recommended clinics."""
    from patients.models import MedicalRecord, Patient
    from clinics.models import ClinicService
    # Get selected medical record and service
    record_id = request.POST.get('medical_record_id')
    service = request.POST.get('service')
    selected_record = None
    if record_id:
        try:
            selected_record = MedicalRecord.objects.get(id=record_id)
        except MedicalRecord.DoesNotExist:
            selected_record = None
    # Filter clinics that accept all relevant fields in the selected medical record
    from clinics.models import Clinic
    compatible_clinics = []
    if selected_record:
        for clinic in Clinic.objects.all():
            incompatible = False
            if getattr(selected_record, 'has_heart_problems', False) and not clinic.accepts_heart_problems:
                incompatible = True
            if (
                getattr(selected_record, 'uses_permanent_catheter', False)
                or getattr(selected_record, 'uses_intermittent_catheter', False)
                or getattr(selected_record, 'uses_urine_tube', False)
            ) and not clinic.accepts_catheter:
                incompatible = True
            if getattr(selected_record, 'uses_wheelchair', False) and not clinic.accepts_wheelchair:
                incompatible = True
            if getattr(selected_record, 'uses_walker', False) and not clinic.accepts_walker:
                incompatible = True
            if getattr(selected_record, 'uses_crutch', False) and not clinic.accepts_crutch:
                incompatible = True
            if getattr(selected_record, 'uses_electric_wheelchair', False) and not clinic.accepts_electric_wheelchair:
                incompatible = True
            if not getattr(selected_record, 'bowel_control', True) and not clinic.accepts_bowel_incontinence:
                incompatible = True
            if not getattr(selected_record, 'urine_control', True) and not clinic.accepts_urine_incontinence:
                incompatible = True
            if getattr(selected_record, 'uses_medical_condom', False) and not clinic.accepts_medical_condom:
                incompatible = True
            if getattr(selected_record, 'uses_diapers', False) and not clinic.accepts_diapers:
                incompatible = True
            if not getattr(selected_record, 'can_breathe_normally', True) and not clinic.accepts_breathing_issues:
                incompatible = True
            if getattr(selected_record, 'uses_feeding_tube', False) and not clinic.accepts_feeding_tube:
                incompatible = True
            if getattr(selected_record, 'uses_stool_tube', False) and not clinic.accepts_stool_tube:
                incompatible = True
            if getattr(selected_record, 'uses_urine_tube', False) and not clinic.accepts_urine_tube:
                incompatible = True
            if getattr(selected_record, 'has_bedsores', False) and not clinic.accepts_bedsores:
                incompatible = True
            if getattr(selected_record, 'has_diabetes', False) and not clinic.accepts_diabetes:
                incompatible = True
            if getattr(selected_record, 'uses_insulin', False) and not clinic.accepts_insulin:
                incompatible = True
            if getattr(selected_record, 'has_high_blood_pressure', False) and not clinic.accepts_high_blood_pressure:
                incompatible = True
            if getattr(selected_record, 'has_infectious_diseases', False) and not clinic.accepts_infectious_diseases:
                incompatible = True
            if getattr(selected_record, 'has_vein_thrombosis', False) and not clinic.accepts_vein_thrombosis:
                incompatible = True
            if getattr(selected_record, 'has_depression', False) and not clinic.accepts_depression:
                incompatible = True
            if not incompatible:
                compatible_clinics.append(clinic)
    params = {
        'medical_record': selected_record,
        'service': service,
        'compatible_clinics': compatible_clinics,
    }
    scorer = getattr(recommender_utils, 'recommend_clinics', None) or getattr(recommender_utils, 'simple_clinic_score', None)
    if scorer is None:
        recommendations = []
    else:
        recommendations = scorer(params)

    # Ensure recommendations are scored and sorted by score (best first).
    try:
        if isinstance(recommendations, list) and len(recommendations) > 0:
            first = recommendations[0]
            # If recommender already returned dicts with a 'score' key, sort them
            if isinstance(first, dict) and 'score' in first:
                recommendations = sorted(recommendations, key=lambda x: x.get('score', 0), reverse=True)
            else:
                # If the recommender returned model instances (Clinic objects), regenerate scored dicts
                # by delegating to the production scorer which knows how to compute scores.
                recommendations = recommender_utils.recommend_clinics({**params, 'compatible_clinics': recommendations})
    except Exception:
        # On any unexpected issue, fall back to an empty list to avoid crashing the view.
        recommendations = []
    # For re-rendering the form
    patient = None
    medical_records = []
    services = []
    if hasattr(request.user, 'user_type') and request.user.user_type == 'patient':
        try:
            patient = Patient.objects.get(user=request.user)
            medical_records = MedicalRecord.objects.filter(patient=patient)
        except Patient.DoesNotExist:
            pass
    services = ClinicService.objects.values_list('service_name', flat=True).distinct().order_by('service_name')
    return render(request, 'recommendations/questionnaire.html', {
        'results': recommendations,
        'medical_records': medical_records,
        'services': services,
        'selected_record': selected_record,
        'selected_service': service,
        'patient': patient,
    })
