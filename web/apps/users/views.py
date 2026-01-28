"""
Views para la app de usuarios
"""

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views import View
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator

from .models import PerfilUsuario


class LoginView(View):
    """Vista de inicio de sesión"""
    template_name = 'users/login.html'

    def get(self, request):
        # Si ya está autenticado, redirigir
        if request.user.is_authenticated:
            return redirect('users:redirect')
        return render(request, self.template_name)

    def post(self, request):
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if not username or not password:
            messages.error(request, 'Por favor ingrese usuario y contraseña')
            return render(request, self.template_name)

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)
                messages.success(request, f'Bienvenido, {user.get_full_name() or user.username}')
                return redirect('users:redirect')
            else:
                messages.error(request, 'Su cuenta está desactivada')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos')

        return render(request, self.template_name)


class LogoutView(View):
    """Vista de cierre de sesión"""

    def get(self, request):
        logout(request)
        messages.info(request, 'Ha cerrado sesión correctamente')
        return redirect('users:login')

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
            messages.error(request, 'Su cuenta está desactivada')
            return redirect('users:login')

        # Redirigir al área asignada
        return redirect(perfil.get_area_url())


@method_decorator(login_required, name='dispatch')
class PerfilView(TemplateView):
    """Vista del perfil del usuario"""
    template_name = 'users/perfil.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['perfil'] = self.request.user.perfil
        except PerfilUsuario.DoesNotExist:
            context['perfil'] = None
        return context
