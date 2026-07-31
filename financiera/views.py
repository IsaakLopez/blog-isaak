from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import (
    ClienteForm, FirmaDocumentoForm, MigracionPaso1Form, MigracionPaso2Form, MigracionPaso3Form,
    PagoCuotaForm, PrestamoForm,
)
from .models import Cliente, CuotaAmortizacion, Prestamo, TransaccionCaja
from .permisos import requiere_permiso
from .services.mora import actualizar_estados_mora

REGISTROS_POR_PAGINA = 25
SESION_MIGRACION = 'migracion_credito'


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
    empleado = getattr(request.user, 'empleado', None)
    return render(request, 'financiera/cliente_detalle.html', {
        'cliente': cliente,
        'puede_eliminar_cliente': bool(
            empleado and empleado.tiene_permiso('eliminar_cliente') and not cliente.prestamos.exists()
        ),
    })


@requiere_permiso('eliminar_cliente')
def cliente_eliminar(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if cliente.prestamos.exists():
        messages.error(request, 'No puedes eliminar un cliente que tiene créditos registrados.')
        return redirect('financiera:cliente_detalle', pk=pk)
    if request.method == 'POST':
        nombre = str(cliente)
        cliente.delete()
        messages.success(request, f'Cliente {nombre} eliminado correctamente.')
        return redirect('financiera:clientes_lista')
    return render(request, 'financiera/cliente_eliminar.html', {'cliente': cliente})


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
    empleado = getattr(request.user, 'empleado', None)
    return render(request, 'financiera/prestamos_lista.html', {
        'prestamos': page_obj,
        'page_obj': page_obj,
        'estado_actual': estado,
        'estados': Prestamo.ESTADO_CHOICES,
        'q': q,
        'puede_migrar_credito': bool(empleado and empleado.tiene_permiso('migrar_credito')),
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
        'puede_eliminar_credito': bool(
            empleado and empleado.tiene_permiso('eliminar_credito') and not prestamo.transacciones.exists()
        ),
    })


@requiere_permiso('eliminar_credito')
def prestamo_eliminar(request, pk):
    prestamo = get_object_or_404(Prestamo.objects.select_related('cliente'), pk=pk)
    if prestamo.transacciones.exists():
        messages.error(request, 'No puedes eliminar un crédito que ya tiene desembolsos o pagos registrados.')
        return redirect('financiera:prestamo_detalle', pk=pk)
    if request.method == 'POST':
        codigo = prestamo.codigo_credito
        prestamo.delete()
        messages.success(request, f'Crédito {codigo} eliminado correctamente.')
        return redirect('financiera:prestamos_lista')
    return render(request, 'financiera/prestamo_eliminar.html', {'prestamo': prestamo})


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


@login_required
def generar_amortizacion_view(request, pk):
    prestamo = get_object_or_404(Prestamo.objects.select_related('cliente'), pk=pk)
    from .services.word_generator import generar_documento_amortizacion
    try:
        buffer = generar_documento_amortizacion(prestamo)
    except (FileNotFoundError, ValueError) as exc:
        messages.error(request, str(exc))
        return redirect('financiera:prestamo_detalle', pk=pk)
    return FileResponse(
        buffer,
        as_attachment=True,
        filename=f'Tabla_Amortizacion_{prestamo.codigo_credito}.docx',
    )


@requiere_permiso('cobrar')
def registrar_pago(request, pk):
    cuota = get_object_or_404(CuotaAmortizacion.objects.select_related('prestamo'), pk=pk)
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
    else:
        form = PagoCuotaForm(initial={'monto': cuota.total_a_pagar})
    return render(request, 'financiera/caja_pago_form.html', {
        'form': form, 'cuota': cuota,
        'saldo_pendiente': cuota.saldo_pendiente,
        'mora_acumulada': cuota.mora_acumulada,
        'total_a_pagar': cuota.total_a_pagar,
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


# --- Asistente de migración de créditos históricos (solo Gerente/Admin) ---

def _serializar_tabla(tabla):
    """Convierte la tabla que devuelve `generar_tabla_amortizacion` (dates y
    Decimals) a algo JSON-serializable para guardarla en la sesión."""
    return [
        {
            'numero_cuota': c['numero_cuota'],
            'fecha_vencimiento': c['fecha_vencimiento'].isoformat(),
            'monto_capital': str(c['monto_capital']),
            'monto_interes': str(c['monto_interes']),
            'monto_total_cuota': str(c['monto_total_cuota']),
            'saldo': str(c['saldo']),
        }
        for c in tabla
    ]


@requiere_permiso('migrar_credito')
def migrar_paso1(request):
    if request.method == 'POST':
        form = MigracionPaso1Form(request.POST)
        if form.is_valid():
            from .services.amortizacion import generar_tabla_amortizacion

            cliente = form.cliente_encontrado
            tabla = generar_tabla_amortizacion(
                monto=form.cleaned_data['monto_solicitado'],
                tasa_interes_mensual=Decimal(form.cleaned_data['tasa_interes_mensual']),
                plazo_meses=form.cleaned_data['plazo_meses'],
                frecuencia_pago=form.cleaned_data['frecuencia_pago'],
                fecha_inicio=form.cleaned_data['fecha_inicio'],
            )
            request.session[SESION_MIGRACION] = {
                'cliente_id': cliente.pk,
                'cliente_nombre': cliente.nombre_completo,
                'cliente_dni': cliente.numero_identificacion,
                'monto_solicitado': str(form.cleaned_data['monto_solicitado']),
                'tasa_interes_mensual': str(form.cleaned_data['tasa_interes_mensual']),
                'plazo_meses': form.cleaned_data['plazo_meses'],
                'frecuencia_pago': form.cleaned_data['frecuencia_pago'],
                'tipo_credito': form.cleaned_data['tipo_credito'],
                'destino': form.cleaned_data['destino'],
                'fecha_inicio': form.cleaned_data['fecha_inicio'].isoformat(),
                'tabla_proyectada': _serializar_tabla(tabla),
            }
            return redirect('financiera:migrar_paso2')
    else:
        form = MigracionPaso1Form()
    return render(request, 'financiera/migrar_paso1.html', {'form': form})


@requiere_permiso('migrar_credito')
def migrar_paso2(request):
    datos = request.session.get(SESION_MIGRACION)
    if not datos:
        messages.error(request, 'Primero completa los datos del crédito.')
        return redirect('financiera:migrar_paso1')

    total_cuotas = len(datos['tabla_proyectada'])
    if request.method == 'POST':
        form = MigracionPaso2Form(request.POST, total_cuotas=total_cuotas)
        if form.is_valid():
            datos['cuotas_pagadas'] = form.cleaned_data['cuotas_pagadas']
            datos.pop('pagos', None)
            request.session[SESION_MIGRACION] = datos
            if datos['cuotas_pagadas'] == 0:
                return redirect('financiera:migrar_resumen')
            return redirect('financiera:migrar_paso3')
    else:
        form = MigracionPaso2Form(total_cuotas=total_cuotas)
    return render(request, 'financiera/migrar_paso2.html', {
        'form': form, 'total_cuotas': total_cuotas, 'datos': datos,
    })


def _cuotas_a_migrar_desde_sesion(datos):
    cantidad = datos['cuotas_pagadas']
    return [
        {
            'numero_cuota': c['numero_cuota'],
            'fecha_vencimiento': date.fromisoformat(c['fecha_vencimiento']),
            'monto_total_cuota': Decimal(c['monto_total_cuota']),
        }
        for c in datos['tabla_proyectada'][:cantidad]
    ]


@requiere_permiso('migrar_credito')
def migrar_paso3(request):
    datos = request.session.get(SESION_MIGRACION)
    if not datos:
        messages.error(request, 'Primero completa los datos del crédito.')
        return redirect('financiera:migrar_paso1')
    if 'cuotas_pagadas' not in datos:
        messages.error(request, 'Primero indica cuántas cuotas están pagadas.')
        return redirect('financiera:migrar_paso2')

    cuotas_a_migrar = _cuotas_a_migrar_desde_sesion(datos)
    if request.method == 'POST':
        form = MigracionPaso3Form(request.POST, cuotas_a_migrar=cuotas_a_migrar)
        if form.is_valid():
            datos['pagos'] = [
                {'numero_cuota': n, 'fecha_pago': f.isoformat(), 'monto': str(m)}
                for n, f, m in form.obtener_pagos_migrados()
            ]
            request.session[SESION_MIGRACION] = datos
            return redirect('financiera:migrar_resumen')
    else:
        form = MigracionPaso3Form(cuotas_a_migrar=cuotas_a_migrar)

    # Django no permite concatenar nombres de campo dinámicamente en el
    # template (`form.fecha_{{ n }}` no funciona), así que se arma aquí la
    # lista de (cuota, campo_fecha, campo_monto) usando el lookup por
    # índice de BoundField (`form['nombre_campo']`), que sí sirve en el
    # template.
    filas = [
        {
            'cuota': cuota,
            'campo_fecha': form[f'fecha_{cuota["numero_cuota"]}'],
            'campo_monto': form[f'monto_{cuota["numero_cuota"]}'],
        }
        for cuota in cuotas_a_migrar
    ]
    return render(request, 'financiera/migrar_paso3.html', {
        'form': form, 'filas': filas, 'datos': datos,
    })


@requiere_permiso('migrar_credito')
def migrar_resumen(request):
    datos = request.session.get(SESION_MIGRACION)
    if not datos:
        messages.error(request, 'Primero completa los datos del crédito.')
        return redirect('financiera:migrar_paso1')
    if 'cuotas_pagadas' not in datos:
        messages.error(request, 'Primero indica cuántas cuotas están pagadas.')
        return redirect('financiera:migrar_paso2')
    if datos['cuotas_pagadas'] > 0 and 'pagos' not in datos:
        messages.error(request, 'Primero registra las fechas y montos de las cuotas pagadas.')
        return redirect('financiera:migrar_paso3')

    cliente = get_object_or_404(Cliente, pk=datos['cliente_id'])
    pagos = datos.get('pagos', [])
    tabla_por_numero = {c['numero_cuota']: c for c in datos['tabla_proyectada']}
    filas_resumen = []
    for pago in pagos:
        programado = tabla_por_numero[pago['numero_cuota']]
        monto_programado = Decimal(programado['monto_total_cuota'])
        monto_a_registrar = Decimal(pago['monto'])
        filas_resumen.append({
            'numero_cuota': pago['numero_cuota'],
            'fecha_programada': programado['fecha_vencimiento'],
            'monto_programado': monto_programado,
            'fecha_pago': pago['fecha_pago'],
            'monto_a_registrar': monto_a_registrar,
            'diferencia': monto_a_registrar - monto_programado,
        })

    if request.method == 'POST':
        from .services.migracion import migrar_credito

        empleado = getattr(request.user, 'empleado', None)
        try:
            prestamo = migrar_credito(
                cliente=cliente,
                monto_solicitado=Decimal(datos['monto_solicitado']),
                tasa_interes_mensual=Decimal(datos['tasa_interes_mensual']),
                plazo_meses=datos['plazo_meses'],
                frecuencia_pago=datos['frecuencia_pago'],
                tipo_credito=datos['tipo_credito'],
                destino=datos['destino'],
                fecha_inicio=date.fromisoformat(datos['fecha_inicio']),
                empleado=empleado,
                pagos_migrados=[
                    (p['numero_cuota'], date.fromisoformat(p['fecha_pago']), Decimal(p['monto']))
                    for p in pagos
                ],
            )
        except ValidationError as exc:
            mensaje = '; '.join(exc.messages) if hasattr(exc, 'messages') else str(exc)
            messages.error(request, f'No se pudo migrar el crédito: {mensaje}')
            return redirect('financiera:migrar_resumen')

        del request.session[SESION_MIGRACION]
        messages.success(request, f'Crédito {prestamo.codigo_credito} migrado correctamente.')
        return redirect('financiera:prestamo_detalle', pk=prestamo.pk)

    return render(request, 'financiera/migrar_resumen.html', {
        'cliente': cliente,
        'datos': datos,
        'filas_resumen': filas_resumen,
        'total_cuotas': len(datos['tabla_proyectada']),
    })


@requiere_permiso('migrar_credito')
def migrar_cancelar(request):
    request.session.pop(SESION_MIGRACION, None)
    return redirect('financiera:prestamos_lista')
