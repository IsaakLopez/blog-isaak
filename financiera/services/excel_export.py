"""Exportación genérica de reportes a Excel (.xlsx)."""
from django.http import HttpResponse
from openpyxl import Workbook

CONTENT_TYPE_XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


def exportar_excel(nombre, encabezados, filas):
    """Arma un .xlsx con una fila de encabezados y una fila por cada elemento
    de `filas` (cada uno una lista/tupla de valores), y lo devuelve listo para
    descargar."""
    libro = Workbook()
    hoja = libro.active
    hoja.title = nombre[:31] or 'Reporte'
    hoja.append(list(encabezados))
    for fila in filas:
        hoja.append(list(fila))

    response = HttpResponse(content_type=CONTENT_TYPE_XLSX)
    response['Content-Disposition'] = f'attachment; filename="{nombre}.xlsx"'
    libro.save(response)
    return response
