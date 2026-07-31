"""Carga de créditos que ya operaban antes de este sistema (con historial de
pagos), respetando fechas reales -- no "empezando hoy" como el flujo normal
de aprobación/desembolso."""
from datetime import datetime, time

from django.db import transaction
from django.utils import timezone

from financiera.models import CuotaAmortizacion, Prestamo, TransaccionCaja
from financiera.services.amortizacion import generar_tabla_amortizacion


def _datetime_medio_dia(fecha):
    """Convierte una fecha (sin hora conocida) a un datetime con timezone,
    usando el mediodía como hora neutra -- para campos `auto_now_add` que
    hay que corregir después de crear el registro."""
    return timezone.make_aware(datetime.combine(fecha, time(12, 0)))


def migrar_credito(
    cliente, monto_solicitado, tasa_interes_mensual, plazo_meses, frecuencia_pago,
    tipo_credito, destino, fecha_inicio, empleado, pagos_migrados,
):
    """Crea un Prestamo ya Desembolsado con su tabla de amortización
    completa a partir de `fecha_inicio` (la fecha real en que empezó el
    crédito, no hoy), y aplica sobre ella los pagos históricos indicados.

    `pagos_migrados`: lista de tuplas `(numero_cuota, fecha_pago, monto)`,
    ordenada por numero_cuota. Cada pago se aplica reutilizando
    `CuotaAmortizacion.registrar_pago(..., fecha_pago=...)`, así que la
    mora, los abonos parciales y los excesos a capital se calculan exacto
    igual que en un cobro en vivo -- solo que con la fecha real del pago,
    no la de hoy.

    Devuelve el Prestamo creado."""
    with transaction.atomic():
        prestamo = Prestamo(
            cliente=cliente,
            monto_solicitado=monto_solicitado,
            tasa_interes_mensual=tasa_interes_mensual,
            plazo_meses=plazo_meses,
            frecuencia_pago=frecuencia_pago,
            tipo_credito=tipo_credito,
            destino=destino,
            estado=Prestamo.ESTADO_DESEMBOLSADO,
            fecha_aprobacion=_datetime_medio_dia(fecha_inicio),
            fecha_desembolso=_datetime_medio_dia(fecha_inicio),
            asesor=empleado,
            aprobado_por=empleado,
            desembolsado_por=empleado,
        )
        prestamo.save()
        # fecha_solicitud es auto_now_add -- se fuerza aparte a la fecha real.
        Prestamo.objects.filter(pk=prestamo.pk).update(fecha_solicitud=_datetime_medio_dia(fecha_inicio))

        tabla = generar_tabla_amortizacion(
            monto=monto_solicitado,
            tasa_interes_mensual=tasa_interes_mensual,
            plazo_meses=plazo_meses,
            frecuencia_pago=frecuencia_pago,
            fecha_inicio=fecha_inicio,
        )
        cuotas_por_numero = {}
        for datos_cuota in tabla:
            cuota = CuotaAmortizacion.objects.create(prestamo=prestamo, **datos_cuota)
            cuotas_por_numero[cuota.numero_cuota] = cuota

        desembolso = TransaccionCaja.objects.create(
            prestamo=prestamo, cajero=empleado,
            tipo_movimiento=TransaccionCaja.TIPO_DESEMBOLSO,
            monto_pagado=monto_solicitado,
        )
        TransaccionCaja.objects.filter(pk=desembolso.pk).update(fecha_hora=_datetime_medio_dia(fecha_inicio))

        for numero_cuota, fecha_pago, monto in pagos_migrados:
            cuota = cuotas_por_numero[numero_cuota]
            cuota.registrar_pago(monto, cajero=empleado, fecha_pago=fecha_pago)

        prestamo.refresh_from_db()
        return prestamo
