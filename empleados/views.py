from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render

from financiera.models import Cliente, Prestamo
from financiera.services.mora import actualizar_estados_mora
from .forms import EmpleadoCreateForm, EmpleadoEditForm, ResetPasswordForm
from .models import Empleado
from .permisos import requiere_admin


def _notificar_credenciales(empleado, password):
    """Envía al empleado su usuario y contraseña por correo. No interrumpe la
    creación de la cuenta si el envío falla (ej. SMTP mal configurado) — el
    ADMIN siempre ve las credenciales en pantalla como respaldo."""
    if not empleado.correo:
        return False
    try:
        send_mail(
            subject='Tu cuenta en MicroFinanzas Pro',
            message=(
                f'Hola {empleado.nombre},\n\n'
                f'Se creó tu cuenta de acceso a MicroFinanzas Pro con cargo "{empleado.get_cargo_display()}".\n\n'
                f'Usuario: {empleado.user.username}\n'
                f'Contraseña: {password}\n\n'
                'Por seguridad, cambia tu contraseña apenas puedas pidiéndole al '
                'Administrador del Sistema que te asigne una nueva desde el panel de Empleados.'
            ),
            from_email=None,
            recipient_list=[empleado.correo],
            fail_silently=False,
        )
        return True
    except Exception:
        return False


@login_required
def home(request):
    actualizar_estados_mora()

    cartera_activa = Prestamo.objects.filter(
        estado__in=[Prestamo.ESTADO_DESEMBOLSADO, Prestamo.ESTADO_EN_MORA]
    ).aggregate(total=Sum('monto_solicitado'))['total'] or 0

    numero_socios = Cliente.objects.count()

    cartera_cerrada_o_activa = Prestamo.objects.filter(
        estado__in=[Prestamo.ESTADO_DESEMBOLSADO, Prestamo.ESTADO_EN_MORA, Prestamo.ESTADO_LIQUIDADO]
    ).count()
    en_mora = Prestamo.objects.filter(estado=Prestamo.ESTADO_EN_MORA).count()
    indice_mora = (en_mora / cartera_cerrada_o_activa * 100) if cartera_cerrada_o_activa else 0

    personal_activo = Empleado.objects.filter(activo=True).count()

    return render(request, 'empleados/home.html', {
        'cartera_activa': cartera_activa,
        'numero_socios': numero_socios,
        'indice_mora': indice_mora,
        'personal_activo': personal_activo,
    })


@login_required
def lista_empleados(request):
    empleados = Empleado.objects.all() # Trae todos los empleados de la DB
    return render(request, 'empleados/lista.html', {'empleados': empleados})


@requiere_admin
def empleado_crear(request):
    if request.method == 'POST':
        form = EmpleadoCreateForm(request.POST)
        if form.is_valid():
            empleado = form.save()
            mensaje = f'Cuenta creada para {empleado} (usuario: {empleado.user.username}).'
            if empleado.correo:
                enviado = _notificar_credenciales(empleado, form.cleaned_data['password1'])
                mensaje += ' Se envió la contraseña por correo.' if enviado else ' No se pudo enviar el correo — comparte la contraseña manualmente.'
            messages.success(request, mensaje)
            return redirect('lista')
    else:
        form = EmpleadoCreateForm()
    return render(request, 'empleados/empleado_form.html', {'form': form, 'modo': 'crear'})


@requiere_admin
def empleado_editar(request, pk):
    empleado = get_object_or_404(Empleado, pk=pk)
    if request.method == 'POST':
        form = EmpleadoEditForm(request.POST, instance=empleado)
        if form.is_valid():
            form.save()
            messages.success(request, f'Empleado {empleado} actualizado correctamente.')
            return redirect('lista')
    else:
        form = EmpleadoEditForm(instance=empleado)
    return render(request, 'empleados/empleado_form.html', {'form': form, 'empleado': empleado, 'modo': 'editar'})


@requiere_admin
def empleado_resetear_password(request, pk):
    empleado = get_object_or_404(Empleado, pk=pk)
    if empleado.user is None:
        messages.error(request, 'Este empleado no tiene una cuenta de usuario vinculada.')
        return redirect('lista')
    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            empleado.user.set_password(form.cleaned_data['password1'])
            empleado.user.save(update_fields=['password'])
            mensaje = f'Contraseña restablecida para {empleado.user.username}.'
            if empleado.correo:
                enviado = _notificar_credenciales(empleado, form.cleaned_data['password1'])
                mensaje += ' Se envió por correo.' if enviado else ' No se pudo enviar el correo — compártela manualmente.'
            messages.success(request, mensaje)
            return redirect('lista')
    else:
        form = ResetPasswordForm()
    return render(request, 'empleados/empleado_resetear_password.html', {'form': form, 'empleado': empleado})
