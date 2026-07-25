"""Actualización automática del estado de mora de cuotas y préstamos."""
from django.utils import timezone

from financiera.models import CuotaAmortizacion, Prestamo


def actualizar_estados_mora(hoy=None):
    hoy = hoy or timezone.localdate()

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
        ids_a_notificar = list(
            Prestamo.objects.filter(
                id__in=prestamos_en_mora, estado=Prestamo.ESTADO_DESEMBOLSADO
            ).values_list('id', flat=True)
        )
        Prestamo.objects.filter(id__in=ids_a_notificar).update(estado=Prestamo.ESTADO_EN_MORA)

        from empleados.services.notificaciones import notificar_mora

        for prestamo in Prestamo.objects.filter(id__in=ids_a_notificar).select_related('cliente', 'asesor'):
            notificar_mora(prestamo)

    return len(prestamos_en_mora)
