from django.contrib import admin

from .models import Cliente, CuotaAmortizacion, Prestamo, TransaccionCaja


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('numero_identificacion', 'nombre_completo', 'asesor')
    list_filter = ('estado_civil', 'genero')
    search_fields = ('numero_identificacion', 'primer_nombre', 'primer_apellido', 'segundo_apellido')


class CuotaAmortizacionInline(admin.TabularInline):
    model = CuotaAmortizacion
    extra = 0
    readonly_fields = ('numero_cuota', 'fecha_vencimiento', 'monto_capital', 'monto_interes', 'monto_total_cuota')
    can_delete = False


@admin.register(Prestamo)
class PrestamoAdmin(admin.ModelAdmin):
    list_display = ('codigo_credito', 'cliente', 'monto_solicitado', 'estado', 'fecha_solicitud')
    list_filter = ('estado', 'frecuencia_pago')
    search_fields = ('codigo_credito', 'cliente__numero_identificacion', 'cliente__primer_nombre', 'cliente__primer_apellido')
    readonly_fields = ('codigo_credito', 'fecha_solicitud', 'fecha_aprobacion', 'fecha_desembolso')
    inlines = [CuotaAmortizacionInline]


@admin.register(CuotaAmortizacion)
class CuotaAmortizacionAdmin(admin.ModelAdmin):
    list_display = ('prestamo', 'numero_cuota', 'fecha_vencimiento', 'monto_total_cuota', 'estado_cuota')
    list_filter = ('estado_cuota',)
    search_fields = ('prestamo__codigo_credito',)


@admin.register(TransaccionCaja)
class TransaccionCajaAdmin(admin.ModelAdmin):
    list_display = ('numero_comprobante', 'prestamo', 'tipo_movimiento', 'monto_pagado', 'cajero', 'fecha_hora')
    list_filter = ('tipo_movimiento',)
    search_fields = ('numero_comprobante', 'prestamo__codigo_credito')
