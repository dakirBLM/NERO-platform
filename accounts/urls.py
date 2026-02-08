from django.urls import path
from .views import CustomLoginView, custom_logout_view, dashboard_redirect_view

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', custom_logout_view, name='logout'),
    path('dashboard/', dashboard_redirect_view, name='dashboard_redirect'),
]