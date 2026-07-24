"""Creación de notificaciones dirigidas por rol/relación (no son iguales para
todos los usuarios): mora avisa al asesor del crédito y a caja/administración,
cambios de estado avisan solo al asesor del crédito, y las acciones de
administración avisan al resto de administradores."""
from django.urls import reverse

from .. import models as empleados_models


def _crear(destinatarios, tipo, mensaje, url=''):
    vistos = set()
    for empleado in destinatarios:
        if empleado is None or empleado.pk in vistos:
            continue
        vistos.add(empleado.pk)
        empleados_models.Notificacion.objects.create(
            destinatario=empleado, tipo=tipo, mensaje=mensaje, url=url,
        )


def notificar_mora(prestamo):
    Empleado = empleados_models.Empleado
    destinatarios = list(
        Empleado.objects.filter(activo=True, cargo__in=[Empleado.CARGO_CAJERO, Empleado.CARGO_ADMIN])
    )
    if prestamo.asesor_id:
        destinatarios.append(prestamo.asesor)
    mensaje = f'El crédito {prestamo.codigo_credito} de {prestamo.cliente} entró en mora.'
    url = reverse('financiera:prestamo_detalle', args=[prestamo.pk])
    _crear(destinatarios, empleados_models.Notificacion.TIPO_MORA, mensaje, url)


def notificar_cambio_estado(prestamo, actor=None):
    if not prestamo.asesor_id:
        return
    if actor is not None and actor.pk == prestamo.asesor_id:
        return
    mensaje = f'El crédito {prestamo.codigo_credito} de {prestamo.cliente} cambió a "{prestamo.get_estado_display()}".'
    url = reverse('financiera:prestamo_detalle', args=[prestamo.pk])
    _crear([prestamo.asesor], empleados_models.Notificacion.TIPO_CREDITO, mensaje, url)


def notificar_admin_accion(mensaje, actor=None, url=''):
    Empleado = empleados_models.Empleado
    destinatarios = Empleado.objects.filter(activo=True, cargo=Empleado.CARGO_ADMIN)
    if actor is not None:
        destinatarios = destinatarios.exclude(pk=actor.pk)
    _crear(destinatarios, empleados_models.Notificacion.TIPO_ADMIN, mensaje, url)
