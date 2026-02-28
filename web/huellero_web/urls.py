"""
URL configuration for huellero_web project.
"""

from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    # Admin de Django
    path('admin/', admin.site.urls),

    # App de usuarios (login, logout, etc.)
    path('users/', include('apps.users.urls', namespace='users')),

    # Redirección de la raíz a login
    path('', lambda request: redirect('users:login')),

    # Área de Logística
    path('logistica/', include('apps.logistica.urls', namespace='logistica')),

]
