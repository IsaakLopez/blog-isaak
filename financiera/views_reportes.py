"""Vistas de la sección Reportes: cada una soporta '?export=xlsx' (con el
mismo filtro de fechas aplicado) para descargar exactamente lo que se ve en
pantalla."""
from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import render

from .models import CuotaAmortizacion, Prestamo, TransaccionCaja
from .services.excel_export import exportar_excel

DIAS_RANGO_DEFECTO = 30


def _rango_fechas(request):
    hoy = date.today()
    desde = request.GET.get('desde') or (hoy - timedelta(days=DIAS_RANGO_DEFECTO)).isoformat()
    hasta = request.GET.get('hasta') or hoy.isoformat()
    return desde, hasta


@login_required
def reportes_index(request):
    return render(request, 'financiera/reportes/index.html')


@login_required
def reporte_colocacion(request):
    desde, hasta = _rango_fechas(request)
    qs = (
        Prestamo.objects.filter(
            fecha_desembolso__date__gte=desde, fecha_desembolso__date__lte=hasta,
        )
        .values('asesor__nombre', 'asesor__apellido')
        .annotate(cantidad=Count('id'), monto_total=Sum('monto_solicitado'))
        .order_by('-monto_total')
    )
    filas = [
        (
            f"{f['asesor__nombre']} {f['asesor__apellido']}".strip() if f['asesor__nombre'] else 'Sin asesor asignado',
            f['cantidad'],
            f['monto_total'] or 0,
        )
        for f in qs
    ]

    if request.GET.get('export') == 'xlsx':
        return exportar_excel('Colocacion_por_asesor', ['Asesor', 'Cantidad de Créditos', 'Monto Total'], filas)

    return render(request, 'financiera/reportes/colocacion.html', {'filas': filas, 'desde': desde, 'hasta': hasta})


@login_required
def reporte_cartera_estado(request):
    estado_display = dict(Prestamo.ESTADO_CHOICES)
    qs = (
        Prestamo.objects.values('estado')
        .annotate(cantidad=Count('id'), monto_total=Sum('monto_solicitado'))
        .order_by('estado')
    )
    filas = [(estado_display.get(f['estado'], f['estado']), f['cantidad'], f['monto_total'] or 0) for f in qs]

    if request.GET.get('export') == 'xlsx':
        return exportar_excel('Cartera_por_estado', ['Estado', 'Cantidad de Créditos', 'Monto Total'], filas)

    return render(request, 'financiera/reportes/cartera_estado.html', {'filas': filas})


@login_required
def reporte_mora(request):
    hoy = date.today()
    cuotas = (
        CuotaAmortizacion.objects.filter(estado_cuota=CuotaAmortizacion.ESTADO_VENCIDO)
        .select_related('prestamo__cliente', 'prestamo__asesor')
        .order_by('fecha_vencimiento')
    )
    filas = []
    for cuota in cuotas:
        dias_atraso = (hoy - cuota.fecha_vencimiento).days
        saldo_pendiente = cuota.monto_total_cuota - cuota.monto_pagado
        filas.append({
            'cuota': cuota,
            'dias_atraso': dias_atraso,
            'saldo_pendiente': saldo_pendiente,
        })

    if request.GET.get('export') == 'xlsx':
        filas_excel = [
            (
                f['cuota'].prestamo.cliente.nombre_completo,
                f['cuota'].prestamo.asesor or 'Sin asesor',
                f['cuota'].prestamo.codigo_credito,
                f['cuota'].numero_cuota,
                f['cuota'].fecha_vencimiento.strftime('%d/%m/%Y'),
                f['dias_atraso'],
                float(f['saldo_pendiente']),
            )
            for f in filas
        ]
        encabezados = ['Cliente', 'Asesor', 'Código Crédito', 'Cuota N°', 'Fecha Vencimiento', 'Días de Atraso', 'Saldo Pendiente']
        return exportar_excel('Mora_cartera_en_riesgo', encabezados, filas_excel)

    return render(request, 'financiera/reportes/mora.html', {'filas': filas})


@login_required
def reporte_cobros(request):
    desde, hasta = _rango_fechas(request)
    qs = (
        TransaccionCaja.objects.filter(
            tipo_movimiento=TransaccionCaja.TIPO_PAGO_CUOTA,
            fecha_hora__date__gte=desde, fecha_hora__date__lte=hasta,
        )
        .annotate(dia=TruncDate('fecha_hora'))
        .values('dia')
        .annotate(total=Sum('monto_pagado'), cantidad=Count('id'))
        .order_by('dia')
    )
    filas = [(f['dia'], f['cantidad'], f['total'] or 0) for f in qs]

    if request.GET.get('export') == 'xlsx':
        filas_excel = [(f[0].strftime('%d/%m/%Y'), f[1], float(f[2])) for f in filas]
        return exportar_excel('Cobros_por_periodo', ['Fecha', 'Cantidad de Pagos', 'Total Cobrado'], filas_excel)

    return render(request, 'financiera/reportes/cobros.html', {'filas': filas, 'desde': desde, 'hasta': hasta})
