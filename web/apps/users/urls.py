"""
URLs para la app de usuarios
"""

from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('redirect/', views.RedirectView.as_view(), name='redirect'),
    path('perfil/', views.PerfilView.as_view(), name='perfil'),
]
