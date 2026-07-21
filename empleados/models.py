from django.conf import settings
from django.db import models


class Empleado(models.Model):
    CARGO_ASESOR = 'ASESOR'
    CARGO_ANALISTA = 'ANALISTA'
    CARGO_GERENTE = 'GERENTE'
    CARGO_CAJERO = 'CAJERO'
    CARGO_ADMIN = 'ADMIN'

    CARGO_CHOICES = [
        (CARGO_ASESOR, 'Asesor de Crédito'),
        (CARGO_ANALISTA, 'Analista de Crédito'),
        (CARGO_GERENTE, 'Gerente / Comité de Crédito'),
        (CARGO_CAJERO, 'Cajero'),
        (CARGO_ADMIN, 'Administrador del Sistema'),
    ]

    # Acciones del flujo de crédito controladas por cargo. ADMIN tiene todas
    # las acciones para cubrir el caso de "un cargo que puede hacer los 2".
    CARGO_PERMISOS = {
        CARGO_ASESOR: {'crear_cliente', 'crear_credito'},
        CARGO_ANALISTA: {'crear_cliente', 'crear_credito', 'evaluar'},
        CARGO_GERENTE: {'evaluar', 'aprobar', 'rechazar'},
        CARGO_CAJERO: {'desembolsar', 'cobrar'},
        CARGO_ADMIN: {
            'crear_cliente', 'crear_credito', 'evaluar', 'aprobar',
            'rechazar', 'desembolsar', 'cobrar',
        },
    }

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='empleado',
    )
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    dni = models.CharField('DNI', max_length=20, unique=True, null=True, blank=True)
    cargo = models.CharField(max_length=20, choices=CARGO_CHOICES, default=CARGO_ASESOR)
    telefono = models.CharField(max_length=20, blank=True)
    correo = models.EmailField(blank=True)
    sucursal = models.CharField(max_length=100, blank=True)
    activo = models.BooleanField('Estado Activo', default=True)
    salario = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Empleado'
        verbose_name_plural = 'Empleados'

    def __str__(self):
        return f'{self.nombre} {self.apellido} ({self.get_cargo_display()})'

    def tiene_permiso(self, accion):
        return accion in self.CARGO_PERMISOS.get(self.cargo, set())

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Mantiene sincronizado el login: un empleado inactivo no debe poder
        # iniciar sesión, sin importar desde dónde se edite (app o /admin/).
        if self.user_id and self.user.is_active != self.activo:
            self.user.is_active = self.activo
            self.user.save(update_fields=['is_active'])
