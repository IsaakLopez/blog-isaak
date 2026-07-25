from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ClienteForm, FirmaDocumentoForm, PagoCuotaForm, PrestamoForm
from .models import Cliente, CuotaAmortizacion, Prestamo, TransaccionCaja
from .permisos import requiere_permiso
from .services.mora import actualizar_estados_mora

REGISTROS_POR_PAGINA = 25


@login_required
def clientes_lista(request):
    q = request.GET.get('q', '').strip()
    clientes_qs = Cliente.objects.select_related('asesor').order_by('primer_apellido', 'primer_nombre')
    if q:
        clientes_qs = clientes_qs.filter(
            Q(primer_nombre__icontains=q) | Q(segundo_nombre__icontains=q) |
            Q(primer_apellido__icontains=q) | Q(segundo_apellido__icontains=q) |
            Q(numero_identificacion__icontains=q)
        )
    page_obj = Paginator(clientes_qs, REGISTROS_POR_PAGINA).get_page(request.GET.get('page'))
    return render(request, 'financiera/clientes_lista.html', {'clientes': page_obj, 'page_obj': page_obj, 'q': q})


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
def validar_cliente_dni(request):
    """Valida al vuelo (AJAX) si existe un cliente con el No. de identificación
    dado, para que el asesor confirme que es la persona correcta antes de
    enviar la solicitud de crédito."""
    numero = request.GET.get('dni', '').strip()
    if not numero:
        return JsonResponse({'encontrado': False})
    cliente = Cliente.objects.filter(numero_identificacion=numero).first()
    if cliente is None:
        return JsonResponse({'encontrado': False})
    return JsonResponse({'encontrado': True, 'nombre': cliente.nombre_completo})


@login_required
def prestamos_lista(request):
    actualizar_estados_mora()
    estado = request.GET.get('estado', '')
    q = request.GET.get('q', '').strip()
    prestamos_qs = Prestamo.objects.select_related('cliente').all()
    if estado:
        prestamos_qs = prestamos_qs.filter(estado=estado)
    if q:
        prestamos_qs = prestamos_qs.filter(
            Q(codigo_credito__icontains=q) |
            Q(cliente__primer_nombre__icontains=q) | Q(cliente__segundo_nombre__icontains=q) |
            Q(cliente__primer_apellido__icontains=q) | Q(cliente__segundo_apellido__icontains=q) |
            Q(cliente__numero_identificacion__icontains=q)
        )
    page_obj = Paginator(prestamos_qs, REGISTROS_POR_PAGINA).get_page(request.GET.get('page'))
    return render(request, 'financiera/prestamos_lista.html', {
        'prestamos': page_obj,
        'page_obj': page_obj,
        'estado_actual': estado,
        'estados': Prestamo.ESTADO_CHOICES,
        'q': q,
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


def _obtener_imagen_firma(request, pk):
    """Procesa el formulario de elección de firma (manual/digital) que
    acompaña al modal de cada documento generado. Devuelve una tupla
    `(imagen_firma, respuesta_error)`:
    - Si la petición es GET (enlace directo, sin pasar por el modal), o si
      se eligió firma manual, devuelve `(None, None)`: el documento se
      genera sin firma, como siempre.
    - Si el formulario no es válido (ej. eligió digital sin subir imagen),
      devuelve `(None, redirect_con_mensaje_de_error)`.
    - Si eligió digital con una imagen válida, devuelve `(imagen_ya_limpia, None)`.
    """
    if request.method != 'POST':
        return None, None

    form = FirmaDocumentoForm(request.POST, request.FILES)
    if not form.is_valid():
        for errores in form.errors.values():
            for error in errores:
                messages.error(request, error)
        return None, redirect('financiera:prestamo_detalle', pk=pk)

    if form.cleaned_data['tipo_firma'] == FirmaDocumentoForm.TIPO_FIRMA_DIGITAL:
        from .services.firma import limpiar_firma_digital

        return limpiar_firma_digital(form.cleaned_data['firma_imagen']), None
    return None, None


@login_required
def generar_solicitud_view(request, pk):
    prestamo = get_object_or_404(Prestamo.objects.select_related('cliente'), pk=pk)
    imagen_firma, respuesta_error = _obtener_imagen_firma(request, pk)
    if respuesta_error:
        return respuesta_error

    from .services.word_generator import generar_solicitud_credito
    try:
        buffer = generar_solicitud_credito(prestamo, imagen_firma=imagen_firma)
    except FileNotFoundError as exc:
        messages.error(request, str(exc))
        return redirect('financiera:prestamo_detalle', pk=pk)
    return FileResponse(
        buffer,
        as_attachment=True,
        filename=f'Solicitud_{prestamo.codigo_credito}.docx',
    )


@login_required
def generar_recibo_desembolso_view(request, pk):
    prestamo = get_object_or_404(Prestamo.objects.select_related('cliente'), pk=pk)
    imagen_firma, respuesta_error = _obtener_imagen_firma(request, pk)
    if respuesta_error:
        return respuesta_error

    from .services.word_generator import generar_recibo_desembolso
    try:
        buffer = generar_recibo_desembolso(prestamo, imagen_firma=imagen_firma)
    except (FileNotFoundError, ValueError) as exc:
        messages.error(request, str(exc))
        return redirect('financiera:prestamo_detalle', pk=pk)
    return FileResponse(
        buffer,
        as_attachment=True,
        filename=f'Recibo_Desembolso_{prestamo.codigo_credito}.docx',
    )


@login_required
def generar_pagare_view(request, pk):
    prestamo = get_object_or_404(Prestamo.objects.select_related('cliente'), pk=pk)
    imagen_firma, respuesta_error = _obtener_imagen_firma(request, pk)
    if respuesta_error:
        return respuesta_error

    from .services.word_generator import generar_pagare
    try:
        buffer = generar_pagare(prestamo, imagen_firma=imagen_firma)
    except (FileNotFoundError, ValueError) as exc:
        messages.error(request, str(exc))
        return redirect('financiera:prestamo_detalle', pk=pk)
    return FileResponse(
        buffer,
        as_attachment=True,
        filename=f'Pagare_{prestamo.codigo_credito}.docx',
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


@login_required
def generar_recibo_pago_view(request, pk):
    transaccion = get_object_or_404(
        TransaccionCaja.objects.select_related('prestamo__cliente', 'cuota'), pk=pk,
    )
    if transaccion.tipo_movimiento != TransaccionCaja.TIPO_PAGO_CUOTA:
        messages.error(request, 'Este movimiento no corresponde a un pago de cuota.')
        return redirect('financiera:prestamo_detalle', pk=transaccion.prestamo_id)

    from .services.word_generator import generar_recibo_pago
    try:
        buffer = generar_recibo_pago(transaccion)
    except FileNotFoundError as exc:
        messages.error(request, str(exc))
        return redirect('financiera:prestamo_detalle', pk=transaccion.prestamo_id)
    return FileResponse(
        buffer,
        as_attachment=True,
        filename=f'Recibo_Pago_{transaccion.numero_comprobante}.docx',
    )
