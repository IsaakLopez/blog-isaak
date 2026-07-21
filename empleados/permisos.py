from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import Empleado


def requiere_admin(vista):
    """Exige login y que el Empleado ligado al usuario tenga cargo ADMIN.
    Solo el Administrador del Sistema puede crear cuentas y asignar cargos."""

    @wraps(vista)
    @login_required
    def wrapper(request, *args, **kwargs):
        empleado = getattr(request.user, 'empleado', None)
        if empleado is None or empleado.cargo != Empleado.CARGO_ADMIN:
            raise PermissionDenied('Solo el Administrador del Sistema puede gestionar empleados.')
        return vista(request, *args, **kwargs)

    return wrapper
