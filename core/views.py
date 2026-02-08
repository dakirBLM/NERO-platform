from django.shortcuts import render
from django.views.generic import TemplateView

class LandingPageView(TemplateView):
    template_name = 'landing_page.html'

class ChoicePageView(TemplateView):
    template_name = 'choice_page.html'