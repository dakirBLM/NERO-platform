from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.contrib import messages

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    
    
    
    def get_success_url(self):
        user = self.request.user
        if user.user_type == 'patient':
            return '/patients/dashboard/'
        elif user.user_type == 'clinic':
            return '/clinics/dashboard/'
        return '/'

def custom_logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('login')

@login_required
def dashboard_redirect_view(request):
    user = request.user
    if user.user_type == 'patient':
        return redirect('patient_dashboard')
    elif user.user_type == 'clinic':
        return redirect('clinic_dashboard')
    else:
        messages.error(request, 'Unknown user type.')
        return redirect('login')