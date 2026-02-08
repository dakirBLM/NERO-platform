from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Patient
from .forms import PatientForm, UserForm

@login_required
def patient_settings_view(request):
    patient = request.user.patient
    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=request.user)
        patient_form = PatientForm(request.POST, request.FILES, instance=patient)
        if user_form.is_valid() and patient_form.is_valid():
            user_form.save()
            patient_form.save()
            messages.success(request, 'Your account information has been updated!')
            return redirect('patient_settings')
    else:
        user_form = UserForm(instance=request.user)
        patient_form = PatientForm(instance=patient)
    return render(request, 'patient/patient_settings.html', {
        'user_form': user_form,
        'form': patient_form,
        'patient': patient,
    })
