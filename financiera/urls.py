from django.urls import path

from . import views

app_name = 'financiera'

urlpatterns = [
    path('clientes/', views.clientes_lista, name='clientes_lista'),
    path('clientes/nuevo/', views.cliente_crear, name='cliente_crear'),
    path('clientes/<int:pk>/', views.cliente_detalle, name='cliente_detalle'),
    path('clientes/<int:pk>/editar/', views.cliente_editar, name='cliente_editar'),

    path('prestamos/', views.prestamos_lista, name='prestamos_lista'),
    path('prestamos/nuevo/', views.prestamo_crear, name='prestamo_crear'),
    path('prestamos/<int:pk>/', views.prestamo_detalle, name='prestamo_detalle'),
    path('prestamos/<int:pk>/transicion/<str:nuevo_estado>/', views.prestamo_transicion, name='prestamo_transicion'),
    path('prestamos/<int:pk>/contrato/', views.generar_contrato_view, name='generar_contrato'),
    path('prestamos/<int:pk>/solicitud/', views.generar_solicitud_view, name='generar_solicitud'),

    path('cuotas/<int:pk>/pagar/', views.registrar_pago, name='registrar_pago'),
]
