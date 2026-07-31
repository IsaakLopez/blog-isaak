from django.urls import path

from . import views, views_reportes

app_name = 'financiera'

urlpatterns = [
    path('clientes/', views.clientes_lista, name='clientes_lista'),
    path('clientes/nuevo/', views.cliente_crear, name='cliente_crear'),
    path('clientes/<int:pk>/', views.cliente_detalle, name='cliente_detalle'),
    path('clientes/<int:pk>/editar/', views.cliente_editar, name='cliente_editar'),
    path('clientes/<int:pk>/eliminar/', views.cliente_eliminar, name='cliente_eliminar'),
    path('clientes/validar-dni/', views.validar_cliente_dni, name='validar_cliente_dni'),

    path('prestamos/', views.prestamos_lista, name='prestamos_lista'),
    path('prestamos/nuevo/', views.prestamo_crear, name='prestamo_crear'),
    path('prestamos/<int:pk>/', views.prestamo_detalle, name='prestamo_detalle'),
    path('prestamos/<int:pk>/eliminar/', views.prestamo_eliminar, name='prestamo_eliminar'),
    path('prestamos/migrar/paso1/', views.migrar_paso1, name='migrar_paso1'),
    path('prestamos/migrar/paso2/', views.migrar_paso2, name='migrar_paso2'),
    path('prestamos/migrar/paso3/', views.migrar_paso3, name='migrar_paso3'),
    path('prestamos/migrar/resumen/', views.migrar_resumen, name='migrar_resumen'),
    path('prestamos/migrar/cancelar/', views.migrar_cancelar, name='migrar_cancelar'),
    path('prestamos/<int:pk>/transicion/<str:nuevo_estado>/', views.prestamo_transicion, name='prestamo_transicion'),
    path('prestamos/<int:pk>/solicitud/', views.generar_solicitud_view, name='generar_solicitud'),
    path('prestamos/<int:pk>/recibo-desembolso/', views.generar_recibo_desembolso_view, name='generar_recibo_desembolso'),
    path('prestamos/<int:pk>/pagare/', views.generar_pagare_view, name='generar_pagare'),
    path('prestamos/<int:pk>/amortizacion/', views.generar_amortizacion_view, name='generar_amortizacion'),

    path('cuotas/<int:pk>/pagar/', views.registrar_pago, name='registrar_pago'),
    path('transacciones/<int:pk>/recibo-pago/', views.generar_recibo_pago_view, name='generar_recibo_pago'),

    path('reportes/', views_reportes.reportes_index, name='reportes_index'),
    path('reportes/colocacion/', views_reportes.reporte_colocacion, name='reporte_colocacion'),
    path('reportes/cartera-por-estado/', views_reportes.reporte_cartera_estado, name='reporte_cartera_estado'),
    path('reportes/mora/', views_reportes.reporte_mora, name='reporte_mora'),
    path('reportes/cobros/', views_reportes.reporte_cobros, name='reporte_cobros'),
]
