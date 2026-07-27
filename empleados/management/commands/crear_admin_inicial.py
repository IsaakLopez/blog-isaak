"""Crea (o actualiza) el usuario administrador inicial a partir de variables
de entorno, para poder entrar al sistema en un despliegue nuevo sin acceso a
una terminal shell (ej. Render en el plan Free, que no incluye Shell).

Se ejecuta en cada `build.sh`; es seguro correrlo varias veces -- si el
usuario ya existe, solo se asegura de que siga siendo superusuario y de que
tenga un Empleado con cargo ADMIN vinculado.

Si no están configuradas las variables de entorno, no hace nada (para no
romper el build en un entorno local de desarrollo)."""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from decouple import config

from empleados.models import Empleado


class Command(BaseCommand):
    help = 'Crea el usuario administrador inicial desde variables de entorno (DJANGO_SUPERUSER_*).'

    def handle(self, *args, **options):
        username = config('DJANGO_SUPERUSER_USERNAME', default='')
        password = config('DJANGO_SUPERUSER_PASSWORD', default='')
        email = config('DJANGO_SUPERUSER_EMAIL', default='')
        nombre = config('DJANGO_SUPERUSER_NOMBRE', default='Administrador')
        apellido = config('DJANGO_SUPERUSER_APELLIDO', default='')

        if not username or not password:
            self.stdout.write('DJANGO_SUPERUSER_USERNAME/PASSWORD no configurados -- se omite.')
            return

        usuario, creado = User.objects.get_or_create(username=username, defaults={'email': email})
        if creado:
            # Solo se fija la contraseña al crearlo -- si ya existía, no se
            # pisa una contraseña que el usuario haya cambiado después desde
            # la app (evita que un redeploy la resetee sin querer).
            usuario.set_password(password)
        usuario.email = email or usuario.email
        usuario.is_staff = True
        usuario.is_superuser = True
        usuario.is_active = True
        usuario.save()

        Empleado.objects.get_or_create(
            user=usuario,
            defaults={'nombre': nombre, 'apellido': apellido, 'cargo': Empleado.CARGO_ADMIN},
        )

        accion = 'creado' if creado else 'actualizado'
        self.stdout.write(self.style.SUCCESS(f'Usuario administrador "{username}" {accion} correctamente.'))
