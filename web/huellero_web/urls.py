"""
URL configuration for huellero_web project.
"""

from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', lambda request: redirect('logistica:index')),
    path('logistica/', include('apps.logistica.urls', namespace='logistica')),
]
