def notificaciones(request):
    """Agrega las notificaciones del empleado logueado a todo template (para
    la campana del topbar, igual que auth/messages ya hacen)."""
    if not request.user.is_authenticated:
        return {}
    empleado = getattr(request.user, 'empleado', None)
    if empleado is None:
        return {}
    return {
        'notificaciones_recientes': empleado.notificaciones.all()[:8],
        'notificaciones_no_leidas': empleado.notificaciones.filter(leida=False).count(),
    }
