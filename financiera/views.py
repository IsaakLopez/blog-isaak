from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ClienteForm, PagoCuotaForm, PrestamoForm
from .models import Cliente, CuotaAmortizacion, Prestamo
from .permisos import requiere_permiso
from .services.mora import actualizar_estados_mora

REGISTROS_POR_PAGINA = 25


@login_required
def clientes_lista(request):
    clientes_qs = Cliente.objects.all().order_by('primer_apellido', 'primer_nombre')
    page_obj = Paginator(clientes_qs, REGISTROS_POR_PAGINA).get_page(request.GET.get('page'))
    return render(request, 'financiera/clientes_lista.html', {'clientes': page_obj, 'page_obj': page_obj})


@requiere_permiso('crear_cliente')
def cliente_crear(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save(commit=False)
            cliente.asesor = getattr(request.user, 'empleado', None)
            cliente.save()
            messages.success(request, 'Cliente registrado correctamente.')
            return redirect('financiera:cliente_detalle', pk=cliente.pk)
    else:
        form = ClienteForm()
    return render(request, 'financiera/cliente_form.html', {'form': form, 'modo': 'crear'})


@requiere_permiso('crear_cliente')
def cliente_editar(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cliente actualizado correctamente.')
            return redirect('financiera:cliente_detalle', pk=cliente.pk)
    else:
        form = ClienteForm(instance=cliente)
    return render(request, 'financiera/cliente_form.html', {'form': form, 'cliente': cliente, 'modo': 'editar'})


@login_required
def cliente_detalle(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    return render(request, 'financiera/cliente_detalle.html', {'cliente': cliente})


@login_required
def prestamos_lista(request):
    actualizar_estados_mora()
    estado = request.GET.get('estado', '')
    prestamos_qs = Prestamo.objects.select_related('cliente').all()
    if estado:
        prestamos_qs = prestamos_qs.filter(estado=estado)
    page_obj = Paginator(prestamos_qs, REGISTROS_POR_PAGINA).get_page(request.GET.get('page'))
    return render(request, 'financiera/prestamos_lista.html', {
        'prestamos': page_obj,
        'page_obj': page_obj,
        'estado_actual': estado,
        'estados': Prestamo.ESTADO_CHOICES,
    })


@requiere_permiso('crear_credito')
def prestamo_crear(request):
    if request.method == 'POST':
        form = PrestamoForm(request.POST)
        if form.is_valid():
            prestamo = form.save(commit=False)
            prestamo.asesor = getattr(request.user, 'empleado', None)
            try:
                prestamo.full_clean()
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                prestamo.save()
                messages.success(request, f'Solicitud {prestamo.codigo_credito} registrada como PENDIENTE.')
                return redirect('financiera:prestamo_detalle', pk=prestamo.pk)
    else:
        form = PrestamoForm()
    return render(request, 'financiera/prestamo_form.html', {'form': form})


@login_required
def prestamo_detalle(request, pk):
    prestamo = get_object_or_404(Prestamo.objects.select_related('cliente'), pk=pk)
    empleado = getattr(request.user, 'empleado', None)

    transiciones_disponibles = []
    for nuevo_estado, accion in prestamo.TRANSICIONES.get(prestamo.estado, {}).items():
        if accion is not None and empleado and empleado.tiene_permiso(accion):
            transiciones_disponibles.append((nuevo_estado, dict(Prestamo.ESTADO_CHOICES)[nuevo_estado]))

    return render(request, 'financiera/prestamo_detalle.html', {
        'prestamo': prestamo,
        'cuotas': prestamo.cuotas.all(),
        'transacciones': prestamo.transacciones.select_related('cuota', 'cajero').all(),
        'transiciones_disponibles': transiciones_disponibles,
        'puede_cobrar': bool(empleado and empleado.tiene_permiso('cobrar')),
    })


@login_required
@require_POST
def prestamo_transicion(request, pk, nuevo_estado):
    prestamo = get_object_or_404(Prestamo, pk=pk)
    empleado = getattr(request.user, 'empleado', None)
    try:
        prestamo.transicionar(nuevo_estado, empleado=empleado)
        messages.success(request, f'Crédito actualizado a "{prestamo.get_estado_display()}".')
    except ValidationError as exc:
        messages.error(request, '; '.join(exc.messages))
    return redirect('financiera:prestamo_detalle', pk=pk)


@login_required
def generar_contrato_view(request, pk):
    prestamo = get_object_or_404(Prestamo, pk=pk)
    if not prestamo.documento_contrato:
        from .services.word_generator import generar_contrato
        try:
            generar_contrato(prestamo)
        except FileNotFoundError as exc:
            messages.error(request, str(exc))
            return redirect('financiera:prestamo_detalle', pk=pk)
    return FileResponse(
        prestamo.documento_contrato.open('rb'),
        as_attachment=True,
        filename=f'{prestamo.codigo_credito}.docx',
    )


@requiere_permiso('cobrar')
def registrar_pago(request, pk):
    cuota = get_object_or_404(CuotaAmortizacion.objects.select_related('prestamo'), pk=pk)
    saldo_pendiente = cuota.monto_total_cuota - cuota.monto_pagado
    if request.method == 'POST':
        form = PagoCuotaForm(request.POST)
        if form.is_valid():
            empleado = getattr(request.user, 'empleado', None)
            try:
                cuota.registrar_pago(
                    form.cleaned_data['monto'],
                    cajero=empleado,
                    numero_comprobante=form.cleaned_data['numero_comprobante'],
                )
                messages.success(request, 'Pago registrado correctamente.')
                return redirect('financiera:prestamo_detalle', pk=cuota.prestamo_id)
            except ValidationError as exc:
                form.add_error('monto', exc)
                saldo_pendiente = cuota.monto_total_cuota - cuota.monto_pagado
    else:
        form = PagoCuotaForm(initial={'monto': saldo_pendiente})
    return render(request, 'financiera/caja_pago_form.html', {
        'form': form, 'cuota': cuota, 'saldo_pendiente': saldo_pendiente,
    })
