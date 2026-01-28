"""
Admin para la app de usuarios
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import PerfilUsuario


class PerfilUsuarioInline(admin.StackedInline):
    """Inline para mostrar el perfil en el admin de usuario"""
    model = PerfilUsuario
    can_delete = False
    verbose_name_plural = 'Perfil'


class UserAdmin(BaseUserAdmin):
    """Admin personalizado para usuarios"""
    inlines = (PerfilUsuarioInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_area', 'is_active')
    list_filter = ('is_active', 'perfil__area')

    def get_area(self, obj):
        try:
            return obj.perfil.get_area_display()
        except PerfilUsuario.DoesNotExist:
            return '-'
    get_area.short_description = 'Área'


# Re-registrar UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    """Admin para perfiles de usuario"""
    list_display = ('user', 'area', 'cargo', 'activo', 'fecha_creacion')
    list_filter = ('area', 'activo')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'cargo')
    raw_id_fields = ('user',)
