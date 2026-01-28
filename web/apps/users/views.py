"""
Views para la app de usuarios
"""

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views import View
from django.utils.decorators import method_decorator

from .models import PerfilUsuario


class LoginView(View):
    """Vista de inicio de sesión"""
    template_name = 'users/login.html'

    def get(self, request):
        # Si ya está autenticado, redirigir
        if request.user.is_authenticated:
            return redirect('users:redirect')

        # Obtener mensaje de la URL (para toasts)
        context = {
            'toast_message': request.GET.get('msg', ''),
            'toast_type': request.GET.get('type', 'info'),
        }
        return render(request, self.template_name, context)

    def post(self, request):
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if not username or not password:
            return render(request, self.template_name, {
                'error': 'Por favor ingrese usuario y contraseña'
            })

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)
                return redirect('users:redirect')
            else:
                return render(request, self.template_name, {
                    'error': 'Su cuenta está desactivada'
                })
        else:
            return render(request, self.template_name, {
                'error': 'Usuario o contraseña incorrectos'
            })


class LogoutView(View):
    """Vista de cierre de sesión"""

    def get(self, request):
        logout(request)
        return redirect('/users/login/?msg=Sesión cerrada correctamente&type=info')

    def post(self, request):
        return self.get(request)


@method_decorator(login_required, name='dispatch')
class RedirectView(View):
    """Redirige al usuario a su área correspondiente"""

    def get(self, request):
        user = request.user

        # Si es superusuario, ir al admin
        if user.is_superuser:
            return redirect('/admin/')

        # Obtener o crear perfil
        try:
            perfil = user.perfil
        except PerfilUsuario.DoesNotExist:
            # Crear perfil por defecto
            perfil = PerfilUsuario.objects.create(user=user, area='logistica')

        # Verificar si el usuario está activo
        if not perfil.activo:
            logout(request)
            return redirect('/users/login/?msg=Su cuenta está desactivada&type=error')

        # Redirigir al área asignada
        return redirect(perfil.get_area_url())
