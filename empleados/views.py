from datetime import date

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.mail import send_mail
from django.db.models import Q, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404, redirect, render

from financiera.models import Cliente, CuotaAmortizacion, Prestamo, TransaccionCaja
from financiera.services.mora import actualizar_estados_mora
from .forms import EmpleadoCreateForm, EmpleadoEditForm, ResetPasswordForm
from .models import Empleado
from .permisos import requiere_admin

MESES_ABREV = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']


def _movimientos_mensuales():
    """Últimos 6 meses de desembolsos vs. cobros, para las barras del panel
    gerencial. Se calcula en el servidor (agregación + % de altura) para no
    depender de ninguna librería de gráficos en el front."""
    primer_dia_mes_actual = date.today().replace(day=1)
    meses = []
    for i in range(5, -1, -1):
        mes = primer_dia_mes_actual.month - i
        anio = primer_dia_mes_actual.year
        while mes <= 0:
            mes += 12
            anio -= 1
        meses.append((anio, mes))

    inicio_rango = date(meses[0][0], meses[0][1], 1)
    totales = (
        TransaccionCaja.objects.filter(fecha_hora__date__gte=inicio_rango)
        .annotate(mes=TruncMonth('fecha_hora'))
        .values('mes', 'tipo_movimiento')
        .annotate(total=Sum('monto_pagado'))
    )
    mapa = {}
    for fila in totales:
        clave = (fila['mes'].year, fila['mes'].month)
        mapa.setdefault(clave, {}).__setitem__(fila['tipo_movimiento'], float(fila['total'] or 0))

    filas = []
    for anio, mes in meses:
        datos = mapa.get((anio, mes), {})
        filas.append({
            'label': MESES_ABREV[mes - 1],
            'desembolsos': datos.get(TransaccionCaja.TIPO_DESEMBOLSO, 0),
            'cobros': datos.get(TransaccionCaja.TIPO_PAGO_CUOTA, 0),
        })

    maximo = max([f['desembolsos'] for f in filas] + [f['cobros'] for f in filas] + [1])
    for f in filas:
        f['pct_desembolsos'] = round(f['desembolsos'] / maximo * 100) if maximo else 0
        f['pct_cobros'] = round(f['cobros'] / maximo * 100) if maximo else 0
    return filas


def _notificar_credenciales(empleado, password):
    """Envía al empleado su usuario y contraseña por correo. No interrumpe la
    creación de la cuenta si el envío falla (ej. SMTP mal configurado) — el
    ADMIN siempre ve las credenciales en pantalla como respaldo."""
    if not empleado.correo:
        return False
    try:
        send_mail(
            subject='Tu cuenta en Portal IMFDC',
            message=(
                f'Hola {empleado.nombre},\n\n'
                f'Se creó tu cuenta de acceso a Portal IMFDC con cargo "{empleado.get_cargo_display()}".\n\n'
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

    empleado = getattr(request.user, 'empleado', None)

    proximos_vencimientos = (
        CuotaAmortizacion.objects
        .filter(estado_cuota__in=[CuotaAmortizacion.ESTADO_PENDIENTE, CuotaAmortizacion.ESTADO_PAGADO_PARCIAL])
        .select_related('prestamo__cliente')
        .order_by('fecha_vencimiento')[:5]
    )

    return render(request, 'empleados/home.html', {
        'cartera_activa': cartera_activa,
        'numero_socios': numero_socios,
        'indice_mora': indice_mora,
        'personal_activo': personal_activo,
        'movimientos_mensuales': _movimientos_mensuales(),
        'proximos_vencimientos': proximos_vencimientos,
        'puede_crear_cliente': bool(empleado and empleado.tiene_permiso('crear_cliente')),
        'puede_crear_credito': bool(empleado and empleado.tiene_permiso('crear_credito')),
    })


@login_required
def lista_empleados(request):
    q = request.GET.get('q', '').strip()
    empleados = Empleado.objects.all() # Trae todos los empleados de la DB
    if q:
        empleados = empleados.filter(
            Q(nombre__icontains=q) | Q(apellido__icontains=q) | Q(dni__icontains=q)
        )
    return render(request, 'empleados/lista.html', {'empleados': empleados, 'q': q})


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


@login_required
def cambiar_mi_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Tu contraseña se actualizó correctamente.')
            return redirect('home')
    else:
        form = PasswordChangeForm(user=request.user)
    return render(request, 'empleados/cambiar_password.html', {'form': form})
