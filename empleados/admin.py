from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User

from .models import Empleado


@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellido', 'dni', 'cargo', 'sucursal', 'activo')
    list_filter = ('cargo', 'activo', 'sucursal')
    search_fields = ('nombre', 'apellido', 'dni', 'correo')


class RestrictedUserAdmin(DjangoUserAdmin):
    """El sistema de permisos por cargo (Empleado.CARGO_PERMISOS) solo tiene
    sentido si nadie puede saltárselo obteniendo acceso a /admin/. Por eso
    solo un superusuario de Django puede otorgar is_staff/is_superuser o
    modificar permisos/grupos de otro usuario."""

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            readonly_fields += ['is_staff', 'is_superuser', 'user_permissions', 'groups']
        return readonly_fields


admin.site.unregister(User)
admin.site.register(User, RestrictedUserAdmin)