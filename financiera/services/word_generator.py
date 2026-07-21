"""Generación automática de contratos Word (docxtpl) a partir de un Préstamo."""
from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from docxtpl import DocxTemplate

from financiera.services.amortizacion import generar_tabla_amortizacion

PLANTILLA_PATH = Path(__file__).resolve().parent.parent / 'templates_docx' / 'contrato_credito.docx'


def generar_contrato(prestamo):
    """Rellena la plantilla oficial con los datos del préstamo y la tabla de
    amortización, y guarda el resultado en `prestamo.documento_contrato`."""
    if not PLANTILLA_PATH.exists():
        raise FileNotFoundError(
            'No existe la plantilla de contrato. Ejecuta '
            '"python manage.py generar_plantilla_contrato" primero.'
        )

    tabla = generar_tabla_amortizacion(
        monto=prestamo.monto_solicitado,
        tasa_interes_anual=prestamo.tasa_interes_anual,
        plazo_meses=prestamo.plazo_meses,
        frecuencia_pago=prestamo.frecuencia_pago,
        fecha_inicio=prestamo.fecha_solicitud.date(),
    )

    cliente = prestamo.cliente
    contexto = {
        'codigo_credito': prestamo.codigo_credito,
        'fecha_aprobacion': prestamo.fecha_aprobacion.strftime('%d/%m/%Y') if prestamo.fecha_aprobacion else '',
        'cliente_nombre': cliente.nombre_completo,
        'cliente_dni': cliente.numero_identificacion,
        'cliente_direccion': cliente.direccion_completa or 'No registrada',
        'monto_solicitado': f'L {prestamo.monto_solicitado:,.2f}',
        'tasa_interes_anual': prestamo.tasa_interes_anual,
        'plazo_meses': prestamo.plazo_meses,
        'frecuencia_pago': prestamo.get_frecuencia_pago_display(),
        'numero_cuotas': len(tabla),
        'cuotas': [
            {
                'numero_cuota': cuota['numero_cuota'],
                'fecha_vencimiento': cuota['fecha_vencimiento'].strftime('%d/%m/%Y'),
                'monto_capital': f"L {cuota['monto_capital']:,.2f}",
                'monto_interes': f"L {cuota['monto_interes']:,.2f}",
                'monto_total_cuota': f"L {cuota['monto_total_cuota']:,.2f}",
            }
            for cuota in tabla
        ],
    }

    documento = DocxTemplate(str(PLANTILLA_PATH))
    documento.render(contexto)

    buffer = BytesIO()
    documento.save(buffer)
    buffer.seek(0)

    nombre_archivo = f'{prestamo.codigo_credito}.docx'
    prestamo.documento_contrato.save(nombre_archivo, ContentFile(buffer.read()), save=True)
    return prestamo.documento_contrato
