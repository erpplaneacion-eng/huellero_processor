from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('logistica', '0003_registro_asistencia'),
    ]

    operations = [
        migrations.DeleteModel(
            name='RegistroAsistencia',
        ),
    ]
