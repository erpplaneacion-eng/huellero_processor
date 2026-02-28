from django.db import models


class Cargo(models.Model):
    """Hoja: horas_cargos — Cargos con límites de horas por día/semana."""
    id_cargo = models.CharField(max_length=50, unique=True)
    cargo = models.CharField(max_length=200)
    numero_colaboradores = models.IntegerField(default=0)
    horas_semana = models.IntegerField(default=0)
    horas_dia = models.FloatField(default=0.0)

    class Meta:
        db_table = 'maestro_cargo'
        verbose_name = 'Cargo'
        verbose_name_plural = 'Cargos'

    def __str__(self):
        return f"{self.id_cargo} — {self.cargo}"


class Horario(models.Model):
    """Hoja: horarios — Franjas horarias de entrada/salida."""
    id_horario = models.IntegerField(unique=True)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()

    class Meta:
        db_table = 'maestro_horario'
        verbose_name = 'Horario'
        verbose_name_plural = 'Horarios'

    def __str__(self):
        return f"Horario {self.id_horario}: {self.hora_inicio} — {self.hora_fin}"


class CargoHorario(models.Model):
    """Hoja: cargos_horarios — Relación muchos a muchos entre Cargo y Horario."""
    cargo = models.ForeignKey(
        Cargo,
        on_delete=models.CASCADE,
        to_field='id_cargo',
        related_name='horarios',
        db_column='id_cargo',
    )
    horario = models.ForeignKey(
        Horario,
        on_delete=models.CASCADE,
        to_field='id_horario',
        related_name='cargos',
        db_column='id_horario',
    )

    class Meta:
        db_table = 'maestro_cargo_horario'
        unique_together = ('cargo', 'horario')
        verbose_name = 'Cargo-Horario'
        verbose_name_plural = 'Cargos-Horarios'

    def __str__(self):
        return f"{self.cargo_id} → Horario {self.horario_id}"


class Empleado(models.Model):
    """Hoja: empleados_ejemplo — Lista de empleados con su cargo asignado."""
    codigo = models.IntegerField()
    nombre = models.CharField(max_length=200)
    documento = models.BigIntegerField(null=True, blank=True)
    cargo = models.ForeignKey(
        Cargo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        to_field='id_cargo',
        related_name='empleados',
        db_column='cargo_id',
    )

    class Meta:
        db_table = 'maestro_empleado'
        verbose_name = 'Empleado'
        verbose_name_plural = 'Empleados'

    def __str__(self):
        return f"{self.nombre} (Cód: {self.codigo})"


class Concepto(models.Model):
    """Hoja: conceptos — Valores disponibles para OBSERVACIONES_1 en el reporte."""
    observaciones = models.TextField()
    procesos = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = 'maestro_concepto'
        verbose_name = 'Concepto'
        verbose_name_plural = 'Conceptos'

    def __str__(self):
        return self.observaciones[:80]
