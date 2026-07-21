from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def requiere_permiso(accion):
    """Exige login y que el Empleado ligado al usuario tenga permiso para
    `accion` según su cargo (Empleado.CARGO_PERMISOS)."""

    def decorador(vista):
        @wraps(vista)
        @login_required
        def wrapper(request, *args, **kwargs):
            empleado = getattr(request.user, 'empleado', None)
            if empleado is None or not empleado.tiene_permiso(accion):
                raise PermissionDenied('Tu cargo no tiene permiso para realizar esta acción.')
            return vista(request, *args, **kwargs)

        return wrapper

    return decorador
