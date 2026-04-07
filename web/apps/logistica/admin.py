from django.contrib import admin

from .models import Cargo, CargoHorario, Concepto, Empleado, Horario


@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display  = ('codigo', 'nombre', 'documento', 'cargo', 'excluido')
    list_filter   = ('excluido', 'cargo')
    search_fields = ('nombre', 'codigo', 'documento')
    list_editable = ('excluido',)
    ordering      = ('nombre',)


@admin.register(Cargo)
class CargoAdmin(admin.ModelAdmin):
    list_display = ('id_cargo', 'cargo', 'horas_dia', 'horas_semana', 'numero_colaboradores')
    search_fields = ('id_cargo', 'cargo')


@admin.register(Horario)
class HorarioAdmin(admin.ModelAdmin):
    list_display = ('id_horario', 'hora_inicio', 'hora_fin')


@admin.register(CargoHorario)
class CargoHorarioAdmin(admin.ModelAdmin):
    list_display = ('cargo', 'horario')
    list_filter  = ('cargo',)


@admin.register(Concepto)
class ConceptoAdmin(admin.ModelAdmin):
    list_display  = ('observaciones', 'procesos')
    search_fields = ('observaciones', 'procesos')
