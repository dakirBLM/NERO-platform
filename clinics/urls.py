from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.clinic_signup_view, name='clinic_signup'),
    path('dashboard/', views.clinic_dashboard_view, name='clinic_dashboard'),
    path('ping/', views.clinic_ping, name='clinic_ping'),
    path('settings/', views.clinic_settings_view, name='clinic_settings'),
    path('detail/<int:clinic_id>/', views.clinic_detail_view, name='clinic_detail'),
    path('detail-clinic/<int:clinic_id>/', views.clinic_detail_clinic_view, name='clinic_datils_clinic'),
    path('manage-gallery/', views.manage_gallery_view, name='manage_gallery'),
    path('delete-gallery-image/<int:image_id>/', views.delete_gallery_image_view, name='delete_gallery_image'),
    path('assign-patient/<int:patient_id>/', views.assign_patient_view, name='assign_patient'),
    path('appointment/create/<int:clinic_id>/', views.create_appointment_view, name='create_appointment'),
    path('appointments/', views.patient_appointments_view, name='patient_appointments'),
    path('clinic-appointments/', views.clinic_appointments_view, name='clinic_appointments'),
    path('appointment/<int:appointment_id>/update-status/', views.update_appointment_status_view, name='update_appointment_status'),
    path('appointment/<int:appointment_id>/update/', views.update_appointment_view, name='update_appointment_view'),
    path('patient/<int:patient_id>/', views.patient_detail_view, name='patient_detail'),
    path('search-patients/', views.search_patients_view, name='search_patients'),
    path('search-patient-clinic/', views.search_patient_clinic_page, name='search_patient_clinic'),
    path('my-posts/', views.clinic_my_posts_view, name='clinic_my_posts'),
    path('my-posts/<int:post_id>/delete/', views.delete_post_view, name='delete_post'),
    
]