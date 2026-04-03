from django.urls import path, re_path
from .views import app_view

urlpatterns = [
    path('', app_view, name='app'),
    re_path(r'^.*$', app_view),  
]
