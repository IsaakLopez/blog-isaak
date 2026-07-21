"""Actualización automática del estado de mora de cuotas y préstamos."""
from datetime import date

from financiera.models import CuotaAmortizacion, Prestamo


def actualizar_estados_mora(hoy=None):
    hoy = hoy or date.today()

    cuotas_vencidas = CuotaAmortizacion.objects.filter(
        estado_cuota__in=[CuotaAmortizacion.ESTADO_PENDIENTE, CuotaAmortizacion.ESTADO_PAGADO_PARCIAL],
        fecha_vencimiento__lt=hoy,
    ).select_related('prestamo')

    prestamos_en_mora = set()
    for cuota in cuotas_vencidas:
        cuota.estado_cuota = CuotaAmortizacion.ESTADO_VENCIDO
        cuota.save(update_fields=['estado_cuota'])
        prestamos_en_mora.add(cuota.prestamo_id)

    if prestamos_en_mora:
        Prestamo.objects.filter(
            id__in=prestamos_en_mora, estado=Prestamo.ESTADO_DESEMBOLSADO
        ).update(estado=Prestamo.ESTADO_EN_MORA)

    return len(prestamos_en_mora)
