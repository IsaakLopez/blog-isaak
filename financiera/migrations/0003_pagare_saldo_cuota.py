from decimal import Decimal

import django.core.validators
from django.db import migrations, models


def recalcular_saldos(apps, schema_editor):
    """Backfill de `saldo` para las cuotas ya existentes: saldo restante del
    préstamo después de pagar el capital de cada cuota, en orden."""
    Prestamo = apps.get_model('financiera', 'Prestamo')
    for prestamo in Prestamo.objects.all():
        saldo = prestamo.monto_solicitado
        for cuota in prestamo.cuotas.order_by('numero_cuota'):
            saldo -= cuota.monto_capital
            cuota.saldo = saldo
            cuota.save(update_fields=['saldo'])


class Migration(migrations.Migration):

    dependencies = [
        ('financiera', '0002_prestamo_tipo_credito'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='prestamo',
            name='documento_contrato',
        ),
        migrations.AddField(
            model_name='cuotaamortizacion',
            name='saldo',
            field=models.DecimalField(
                decimal_places=2, default=Decimal('0'), max_digits=12, verbose_name='Saldo después de esta cuota',
                validators=[django.core.validators.MinValueValidator(Decimal('0'), message='No puede ser negativo.')],
            ),
            preserve_default=False,
        ),
        migrations.RunPython(recalcular_saldos, migrations.RunPython.noop),
    ]
