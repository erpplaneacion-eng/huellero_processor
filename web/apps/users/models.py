"""
Modelos para la app de usuarios
"""

from django.db import models
from django.contrib.auth.models import User


class PerfilUsuario(models.Model):
    """Perfil extendido del usuario con área asignada"""

    AREAS_CHOICES = [
        ('logistica', 'Logística'),
        ('supervision', 'Supervisión'),
        ('produccion', 'Producción'),
        ('mantenimiento', 'Mantenimiento'),
        ('admin', 'Administrador'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    area = models.CharField(
        max_length=50,
        choices=AREAS_CHOICES,
        default='logistica',
        verbose_name='Área asignada'
    )
    cargo = models.CharField(max_length=100, blank=True, verbose_name='Cargo')
    activo = models.BooleanField(default=True, verbose_name='Usuario activo')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Perfil de Usuario'
        verbose_name_plural = 'Perfiles de Usuarios'

    def __str__(self):
        return f"{self.user.username} - {self.get_area_display()}"

    def get_area_url(self):
        """Retorna la URL del área asignada"""
        if self.area == 'admin':
            return '/admin/'
        return f'/{self.area}/'
