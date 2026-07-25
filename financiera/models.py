from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from empleados.models import Empleado

MONTO_POSITIVO = MinValueValidator(Decimal('0.01'), message='Debe ser mayor a cero.')
VALOR_NO_NEGATIVO = MinValueValidator(Decimal('0'), message='No puede ser negativo.')


class Cliente(models.Model):
    TIPO_ID_IDENTIDAD = 'IDENTIDAD'
    TIPO_ID_CARNET_RESIDENCIA = 'CARNET_RESIDENCIA'
    TIPO_ID_PASAPORTE = 'PASAPORTE'
    TIPO_IDENTIFICACION_CHOICES = [
        (TIPO_ID_IDENTIDAD, 'Identidad'),
        (TIPO_ID_CARNET_RESIDENCIA, 'Carnet de Residencia'),
        (TIPO_ID_PASAPORTE, 'Pasaporte'),
    ]

    GENERO_FEMENINO = 'FEMENINO'
    GENERO_MASCULINO = 'MASCULINO'
    GENERO_CHOICES = [
        (GENERO_FEMENINO, 'Femenino'),
        (GENERO_MASCULINO, 'Masculino'),
    ]

    NACIONALIDAD_HONDURENA = 'HONDURENA'
    NACIONALIDAD_EXTRANJERA = 'EXTRANJERA'
    NACIONALIDAD_CHOICES = [
        (NACIONALIDAD_HONDURENA, 'Hondureña'),
        (NACIONALIDAD_EXTRANJERA, 'Extranjera'),
    ]

    ESTADO_CIVIL_SOLTERO = 'SOLTERO'
    ESTADO_CIVIL_CASADO = 'CASADO'
    ESTADO_CIVIL_DIVORCIADO = 'DIVORCIADO'
    ESTADO_CIVIL_UNION_LIBRE = 'UNION_LIBRE'
    ESTADO_CIVIL_CHOICES = [
        (ESTADO_CIVIL_SOLTERO, 'Soltero(a)'),
        (ESTADO_CIVIL_CASADO, 'Casado(a)'),
        (ESTADO_CIVIL_DIVORCIADO, 'Divorciado(a)'),
        (ESTADO_CIVIL_UNION_LIBRE, 'Unión libre'),
    ]

    TIPO_EMPRESA_PRIVADA = 'PRIVADA'
    TIPO_EMPRESA_PUBLICA = 'PUBLICA'
    TIPO_EMPRESA_ONG = 'ONG'
    TIPO_EMPRESA_CHOICES = [
        (TIPO_EMPRESA_PRIVADA, 'Empresa privada'),
        (TIPO_EMPRESA_PUBLICA, 'Empresa pública'),
        (TIPO_EMPRESA_ONG, 'ONG'),
    ]

    TIPO_EMPLEADO_INDEPENDIENTE = 'INDEPENDIENTE'
    TIPO_EMPLEADO_PROPIETARIO = 'PROPIETARIO'
    TIPO_EMPLEADO_COMERCIANTE = 'COMERCIANTE'
    TIPO_EMPLEADO_CHOICES = [
        (TIPO_EMPLEADO_INDEPENDIENTE, 'Profesional independiente'),
        (TIPO_EMPLEADO_PROPIETARIO, 'Propietario'),
        (TIPO_EMPLEADO_COMERCIANTE, 'Comerciante individual'),
    ]

    RANGO_SALARIO_CHOICES = [
        ('RANGO_1', 'L 0 – L 8,500.00'),
        ('RANGO_2', 'L 8,501.00 – L 26,500.00'),
        ('RANGO_3', 'L 26,501.00 – L 54,000.00'),
        ('RANGO_4', 'L 54,001.00 – L 108,000.00'),
        ('RANGO_5', 'L 108,001.00 – L 150,000.00'),
        ('RANGO_6', 'L 150,001.00 – L 200,000.00'),
        ('RANGO_7', 'L 200,001.00 en adelante'),
    ]

    # --- 1. Datos de identificación personal ---
    primer_nombre = models.CharField(max_length=75)
    segundo_nombre = models.CharField(max_length=75, blank=True)
    primer_apellido = models.CharField(max_length=75)
    segundo_apellido = models.CharField(max_length=75, blank=True)
    fecha_nacimiento = models.DateField()
    lugar_nacimiento = models.CharField(max_length=150)
    tipo_identificacion = models.CharField(max_length=20, choices=TIPO_IDENTIFICACION_CHOICES, default=TIPO_ID_IDENTIDAD)
    numero_identificacion = models.CharField('No. de Identificación', max_length=20, unique=True, db_index=True)
    genero = models.CharField(max_length=10, choices=GENERO_CHOICES)
    nacionalidad = models.CharField(max_length=15, choices=NACIONALIDAD_CHOICES)
    profesion_ocupacion_oficio = models.CharField('Profesión / Ocupación / Oficio', max_length=150)

    # --- 2. Información de contacto y domicilio ---
    telefono_fijo = models.CharField(max_length=20, blank=True)
    celular = models.CharField(max_length=20)
    email_personal = models.EmailField(blank=True)
    direccion_colonia_barrio = models.CharField('Colonia / Barrio / Aldea', max_length=150)
    calle_avenida = models.CharField('Calle / Avenida', max_length=150)
    numero_casa = models.CharField('No. de Casa', max_length=30, blank=True)
    punto_referencia = models.CharField(max_length=255, blank=True)
    municipio = models.CharField(max_length=100)
    departamento = models.CharField(max_length=100)
    pais = models.CharField(max_length=100, default='Honduras')

    # --- 3. Estado civil y datos familiares ---
    estado_civil = models.CharField(max_length=15, choices=ESTADO_CIVIL_CHOICES)
    numero_dependientes = models.PositiveIntegerField(default=0)
    nombre_conyuge = models.CharField(max_length=150, blank=True)
    conyuge_telefono_fijo = models.CharField(max_length=20, blank=True)
    conyuge_celular = models.CharField(max_length=20, blank=True)
    conyuge_empresa = models.CharField('Empresa donde labora el cónyuge', max_length=150, blank=True)

    # --- 4. Referencias personales (2 fijas) ---
    ref1_nombre = models.CharField('Referencia 1 - Nombre completo', max_length=150)
    ref1_telefono_fijo = models.CharField('Referencia 1 - Teléfono fijo', max_length=20, blank=True)
    ref1_celular = models.CharField('Referencia 1 - Celular', max_length=20)
    ref2_nombre = models.CharField('Referencia 2 - Nombre completo', max_length=150, blank=True)
    ref2_telefono_fijo = models.CharField('Referencia 2 - Teléfono fijo', max_length=20, blank=True)
    ref2_celular = models.CharField('Referencia 2 - Celular', max_length=20, blank=True)

    # --- 5. Información profesional y laboral ---
    tipo_empresa = models.CharField(max_length=15, choices=TIPO_EMPRESA_CHOICES)
    tipo_empleado = models.CharField(max_length=15, choices=TIPO_EMPLEADO_CHOICES)
    empresa_nombre = models.CharField('Nombre de la empresa en la que labora', max_length=150)
    empresa_fecha_ingreso = models.DateField()
    empresa_anios_laborando = models.DecimalField(
        'Años laborando', max_digits=4, decimal_places=1, validators=[VALOR_NO_NEGATIVO]
    )
    cargo_actual = models.CharField(max_length=100)
    empresa_telefono = models.CharField(max_length=20)
    empresa_email = models.EmailField(blank=True)
    empresa_direccion = models.CharField(max_length=255)
    empresa_ciudad = models.CharField(max_length=100)
    empresa_municipio = models.CharField(max_length=100)
    empresa_departamento = models.CharField(max_length=100)
    gerente_rrhh_nombre = models.CharField('Nombre del Gerente / Jefe de Recursos Humanos', max_length=150, blank=True)
    jefe_inmediato_nombre = models.CharField('Nombre del Jefe inmediato', max_length=150, blank=True)

    # --- 6. Información financiera ---
    actividad_economica = models.CharField('Actividad Económica / Negocio', max_length=150, blank=True)
    ingresos_mensuales = models.DecimalField(
        'Ingreso Mensual', max_digits=12, decimal_places=2, default=0, validators=[VALOR_NO_NEGATIVO]
    )
    rango_salario = models.CharField(max_length=10, choices=RANGO_SALARIO_CHOICES)

    asesor = models.ForeignKey(
        Empleado, on_delete=models.SET_NULL, null=True, blank=True, related_name='clientes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'

    def __str__(self):
        return f'{self.nombre_completo} ({self.numero_identificacion})'

    def clean(self):
        # Los datos del cónyuge solo aplican si el estado civil es Casado(a) o Unión libre.
        conyuge_requerido = self.estado_civil in (self.ESTADO_CIVIL_CASADO, self.ESTADO_CIVIL_UNION_LIBRE)
        if conyuge_requerido and not self.nombre_conyuge:
            raise ValidationError({'nombre_conyuge': 'Requerido cuando el estado civil es Casado(a) o Unión libre.'})

    @property
    def nombre_completo(self):
        partes = [self.primer_nombre, self.segundo_nombre, self.primer_apellido, self.segundo_apellido]
        return ' '.join(parte for parte in partes if parte)

    @property
    def direccion_completa(self):
        partes = [
            self.calle_avenida, f'Casa No. {self.numero_casa}' if self.numero_casa else '',
            self.direccion_colonia_barrio, self.municipio, self.departamento, self.pais,
        ]
        return ', '.join(parte for parte in partes if parte)


class Prestamo(models.Model):
    FRECUENCIA_SEMANAL = 'SEMANAL'
    FRECUENCIA_QUINCENAL = 'QUINCENAL'
    FRECUENCIA_MENSUAL = 'MENSUAL'

    FRECUENCIA_CHOICES = [
        (FRECUENCIA_SEMANAL, 'Semanal'),
        (FRECUENCIA_QUINCENAL, 'Quincenal'),
        (FRECUENCIA_MENSUAL, 'Mensual'),
    ]

    TIPO_CREDITO_PERSONAL = 'PERSONAL'
    TIPO_CREDITO_HIPOTECARIO = 'HIPOTECARIO'
    TIPO_CREDITO_CHOICES = [
        (TIPO_CREDITO_PERSONAL, 'Personal'),
        (TIPO_CREDITO_HIPOTECARIO, 'Hipotecario'),
    ]

    DESTINO_MEJORAS = 'MEJORAS'
    DESTINO_PAGO_DEUDA = 'PAGO_DEUDA'
    DESTINO_COLEGIATURA = 'COLEGIATURA'
    DESTINO_GASTOS_MEDICOS = 'GASTOS_MEDICOS'
    DESTINO_CONSUMO = 'CONSUMO'
    DESTINO_CHOICES = [
        (DESTINO_MEJORAS, 'Mejoras'),
        (DESTINO_PAGO_DEUDA, 'Pago de deuda'),
        (DESTINO_COLEGIATURA, 'Pago de colegiatura'),
        (DESTINO_GASTOS_MEDICOS, 'Gastos médicos'),
        (DESTINO_CONSUMO, 'Consumo'),
    ]

    ESTADO_PENDIENTE = 'PENDIENTE'
    ESTADO_EN_REVISION = 'EN_REVISION'
    ESTADO_APROBADO = 'APROBADO'
    ESTADO_DESEMBOLSADO = 'DESEMBOLSADO'
    ESTADO_EN_MORA = 'EN_MORA'
    ESTADO_LIQUIDADO = 'LIQUIDADO'
    ESTADO_RECHAZADO = 'RECHAZADO'
    ESTADO_CANCELADO = 'CANCELADO'

    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_EN_REVISION, 'En Revisión'),
        (ESTADO_APROBADO, 'Aprobado'),
        (ESTADO_DESEMBOLSADO, 'Desembolsado / Activo'),
        (ESTADO_EN_MORA, 'En Mora'),
        (ESTADO_LIQUIDADO, 'Liquidado / Pagado'),
        (ESTADO_RECHAZADO, 'Rechazado'),
        (ESTADO_CANCELADO, 'Cancelado'),
    ]

    # Mapa de la máquina de estados: estado_actual -> {estado_nuevo: accion_requerida}
    # accion_requerida es None para transiciones automáticas del sistema (mora/liquidación).
    TRANSICIONES = {
        ESTADO_PENDIENTE: {
            ESTADO_EN_REVISION: 'evaluar',
            ESTADO_RECHAZADO: 'rechazar',
            ESTADO_CANCELADO: 'crear_credito',
        },
        ESTADO_EN_REVISION: {
            ESTADO_APROBADO: 'aprobar',
            ESTADO_RECHAZADO: 'rechazar',
        },
        ESTADO_APROBADO: {
            ESTADO_DESEMBOLSADO: 'desembolsar',
            ESTADO_CANCELADO: 'aprobar',
        },
        ESTADO_DESEMBOLSADO: {
            ESTADO_EN_MORA: None,
            ESTADO_LIQUIDADO: None,
        },
        ESTADO_EN_MORA: {
            ESTADO_DESEMBOLSADO: None,
            ESTADO_LIQUIDADO: None,
        },
    }

    codigo_credito = models.CharField(max_length=20, unique=True, editable=False)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='prestamos')
    monto_solicitado = models.DecimalField(max_digits=12, decimal_places=2, validators=[MONTO_POSITIVO])
    tasa_interes_mensual = models.DecimalField(max_digits=5, decimal_places=2, validators=[VALOR_NO_NEGATIVO])
    plazo_meses = models.PositiveIntegerField(validators=[MinValueValidator(1, message='Debe ser al menos 1 mes.')])
    frecuencia_pago = models.CharField(max_length=15, choices=FRECUENCIA_CHOICES, default=FRECUENCIA_MENSUAL)
    tipo_credito = models.CharField(
        'Tipo de Crédito', max_length=15, choices=TIPO_CREDITO_CHOICES, default=TIPO_CREDITO_PERSONAL,
    )
    destino = models.CharField('Destino del préstamo', max_length=20, choices=DESTINO_CHOICES)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=ESTADO_PENDIENTE)

    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    fecha_desembolso = models.DateTimeField(null=True, blank=True)

    asesor = models.ForeignKey(
        Empleado, on_delete=models.SET_NULL, null=True, blank=True, related_name='prestamos_asesorados'
    )
    aprobado_por = models.ForeignKey(
        Empleado, on_delete=models.SET_NULL, null=True, blank=True, related_name='prestamos_aprobados'
    )
    desembolsado_por = models.ForeignKey(
        Empleado, on_delete=models.SET_NULL, null=True, blank=True, related_name='prestamos_desembolsados'
    )

    class Meta:
        verbose_name = 'Préstamo'
        verbose_name_plural = 'Préstamos'
        ordering = ['-fecha_solicitud']

    def __str__(self):
        return f'{self.codigo_credito} - {self.cliente}'

    # NOTA: la Regla de Negocio 1 (bloquear solicitud si el cliente no está
    # verificado como "Apto") está temporalmente desactivada a pedido del
    # usuario mientras se reconstruye el flujo de revisión de estado
    # crediticio. Reintroducir aquí cuando ese flujo exista.

    def save(self, *args, **kwargs):
        if not self.codigo_credito:
            self.codigo_credito = self._generar_codigo_credito()
        super().save(*args, **kwargs)

    @classmethod
    def _generar_codigo_credito(cls):
        anio = timezone.localdate().year
        prefijo = f'CR-{anio}-'
        ultimo = (
            cls.objects.filter(codigo_credito__startswith=prefijo)
            .order_by('-codigo_credito')
            .first()
        )
        siguiente = int(ultimo.codigo_credito.split('-')[-1]) + 1 if ultimo else 1
        return f'{prefijo}{siguiente:04d}'

    def transicionar(self, nuevo_estado, empleado=None, automatico=False):
        """Aplica una transición de estado validando permisos por cargo y el
        grafo de transiciones permitidas. `automatico=True` se usa para las
        transiciones que dispara el propio sistema (mora/liquidación)."""
        transiciones_validas = self.TRANSICIONES.get(self.estado, {})
        if nuevo_estado not in transiciones_validas:
            raise ValidationError(
                f'No se puede pasar de "{self.get_estado_display()}" a '
                f'"{dict(self.ESTADO_CHOICES).get(nuevo_estado, nuevo_estado)}".'
            )

        accion = transiciones_validas[nuevo_estado]
        if accion is not None and not automatico:
            if empleado is None or not empleado.tiene_permiso(accion):
                raise ValidationError(
                    'Tu cargo no tiene permiso para realizar esta acción sobre el crédito.'
                )

        estado_anterior = self.estado
        self.estado = nuevo_estado

        if nuevo_estado == self.ESTADO_APROBADO:
            self.fecha_aprobacion = timezone.now()
            self.aprobado_por = empleado
        elif nuevo_estado == self.ESTADO_DESEMBOLSADO and estado_anterior != self.ESTADO_EN_MORA:
            self.fecha_desembolso = timezone.now()
            self.desembolsado_por = empleado

        self.save()

        from empleados.services.notificaciones import notificar_cambio_estado

        notificar_cambio_estado(self, actor=empleado)

        if nuevo_estado == self.ESTADO_DESEMBOLSADO and estado_anterior == self.ESTADO_APROBADO:
            self._activar_desembolso(empleado)

        return self

    def _activar_desembolso(self, empleado):
        from financiera.services.amortizacion import generar_tabla_amortizacion

        tabla = generar_tabla_amortizacion(
            monto=self.monto_solicitado,
            tasa_interes_mensual=self.tasa_interes_mensual,
            plazo_meses=self.plazo_meses,
            frecuencia_pago=self.frecuencia_pago,
            fecha_inicio=timezone.localdate(self.fecha_desembolso) if self.fecha_desembolso else timezone.localdate(),
        )
        for cuota in tabla:
            CuotaAmortizacion.objects.create(prestamo=self, **cuota)

        TransaccionCaja.objects.create(
            prestamo=self,
            cajero=empleado,
            tipo_movimiento=TransaccionCaja.TIPO_DESEMBOLSO,
            monto_pagado=self.monto_solicitado,
        )


class CuotaAmortizacion(models.Model):
    ESTADO_PENDIENTE = 'PENDIENTE'
    ESTADO_PAGADO_PARCIAL = 'PAGADO_PARCIAL'
    ESTADO_PAGADO = 'PAGADO'
    ESTADO_VENCIDO = 'VENCIDO'

    ESTADO_CUOTA_CHOICES = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_PAGADO_PARCIAL, 'Pagado Parcial'),
        (ESTADO_PAGADO, 'Pagado'),
        (ESTADO_VENCIDO, 'Vencido'),
    ]

    # Mora: 2% simple por cada mes calendario completo de atraso, sobre el
    # saldo pendiente DE LA CUOTA (no el monto original) -- si la cuota tuvo
    # un abono parcial, la mora se calcula solo sobre lo que sigue debiendo.
    TASA_MORA_MENSUAL = Decimal('0.02')
    DIAS_POR_MES_MORA = 30

    prestamo = models.ForeignKey(Prestamo, on_delete=models.CASCADE, related_name='cuotas')
    numero_cuota = models.PositiveIntegerField()
    fecha_vencimiento = models.DateField()
    monto_capital = models.DecimalField(max_digits=12, decimal_places=2, validators=[VALOR_NO_NEGATIVO])
    monto_interes = models.DecimalField(max_digits=12, decimal_places=2, validators=[VALOR_NO_NEGATIVO])
    monto_total_cuota = models.DecimalField(max_digits=12, decimal_places=2, validators=[MONTO_POSITIVO])
    saldo = models.DecimalField(
        'Saldo después de esta cuota', max_digits=12, decimal_places=2, validators=[VALOR_NO_NEGATIVO],
    )
    estado_cuota = models.CharField(max_length=20, choices=ESTADO_CUOTA_CHOICES, default=ESTADO_PENDIENTE)

    class Meta:
        verbose_name = 'Cuota de Amortización'
        verbose_name_plural = 'Tabla de Amortización'
        ordering = ['prestamo', 'numero_cuota']
        unique_together = ('prestamo', 'numero_cuota')

    def __str__(self):
        return f'{self.prestamo.codigo_credito} - Cuota {self.numero_cuota}'

    @property
    def monto_pagado(self):
        total = self.transacciones.filter(
            tipo_movimiento=TransaccionCaja.TIPO_PAGO_CUOTA,
        ).aggregate(total=models.Sum('monto_pagado'))['total']
        # OJO: se redondea a 2 decimales -- en SQLite, Sum() sobre un
        # DecimalField pasa por REAL (punto flotante) y puede devolver
        # residuos de precisión (ej. 1234.5600000000001).
        return (total or Decimal('0')).quantize(Decimal('0.01'))

    @property
    def saldo_pendiente(self):
        """Lo que falta para terminar de pagar ESTA cuota (sin contar mora)."""
        return (self.monto_total_cuota - self.monto_pagado).quantize(Decimal('0.01'))

    @property
    def dias_atraso(self):
        if self.estado_cuota == self.ESTADO_PAGADO or self.saldo_pendiente <= 0:
            return 0
        dias = (timezone.localdate() - self.fecha_vencimiento).days
        return max(dias, 0)

    @property
    def meses_atraso(self):
        return self.dias_atraso // self.DIAS_POR_MES_MORA

    @property
    def mora_pagada(self):
        total = self.transacciones.filter(
            tipo_movimiento=TransaccionCaja.TIPO_MORA,
        ).aggregate(total=models.Sum('monto_pagado'))['total']
        return (total or Decimal('0')).quantize(Decimal('0.01'))

    @property
    def mora_generada(self):
        """Mora bruta generada hasta hoy: 2% simple por cada mes completo de
        atraso, sobre el saldo pendiente ACTUAL de la cuota (si tuvo un
        abono, la mora se recalcula sobre lo que sigue debiendo, no sobre el
        monto original). No descuenta lo ya pagado de mora -- para eso está
        `mora_acumulada`."""
        meses = self.meses_atraso
        saldo = self.saldo_pendiente
        if meses <= 0 or saldo <= 0:
            return Decimal('0.00')
        return (self.TASA_MORA_MENSUAL * meses * saldo).quantize(Decimal('0.01'))

    @property
    def mora_acumulada(self):
        """Mora que todavía falta pagar (la generada hasta hoy, menos lo que
        ya se pagó de mora)."""
        pendiente = self.mora_generada - self.mora_pagada
        return pendiente if pendiente > 0 else Decimal('0.00')

    @property
    def total_a_pagar(self):
        """Lo que el cliente debe traer hoy para ponerse al día con esta
        cuota: su saldo pendiente más la mora acumulada."""
        return self.saldo_pendiente + self.mora_acumulada

    def registrar_pago(self, monto, cajero, numero_comprobante=''):
        """Aplica un pago sobre esta cuota. Acepta cualquier monto positivo,
        no solo el exacto de la cuota:
        - Si es MENOS que el saldo pendiente, es un abono parcial (la cuota
          queda "Pagado Parcial").
        - Si alcanza para la cuota y sobra, primero se cobra la mora
          acumulada (si hay) y luego el resto se aplica como abono a
          capital, reduciendo el saldo restante del préstamo (esta cuota y
          las futuras) -- el préstamo se termina de pagar antes, las cuotas
          futuras mantienen su monto tal como están en la tabla original."""
        monto = Decimal(monto)
        if monto <= 0:
            raise ValidationError('El monto a pagar debe ser mayor a cero.')

        saldo_cuota = self.saldo_pendiente
        mora = self.mora_acumulada
        tope_maximo = saldo_cuota + mora + self.saldo
        if monto > tope_maximo:
            raise ValidationError(
                f'El monto (L {monto:,.2f}) excede el total pendiente del préstamo, '
                f'incluyendo mora (L {tope_maximo:,.2f}).'
            )

        restante = monto
        comprobante_usado = False
        transacciones_creadas = []

        def _siguiente_comprobante():
            nonlocal comprobante_usado
            if comprobante_usado or not numero_comprobante:
                return ''
            comprobante_usado = True
            return numero_comprobante

        if mora > 0 and restante > 0:
            monto_mora = min(restante, mora)
            transacciones_creadas.append(TransaccionCaja.objects.create(
                prestamo=self.prestamo, cuota=self, cajero=cajero,
                tipo_movimiento=TransaccionCaja.TIPO_MORA,
                monto_pagado=monto_mora,
                numero_comprobante=_siguiente_comprobante(),
            ))
            restante -= monto_mora

        if saldo_cuota > 0 and restante > 0:
            monto_cuota = min(restante, saldo_cuota)
            transacciones_creadas.append(TransaccionCaja.objects.create(
                prestamo=self.prestamo, cuota=self, cajero=cajero,
                tipo_movimiento=TransaccionCaja.TIPO_PAGO_CUOTA,
                monto_pagado=monto_cuota,
                numero_comprobante=_siguiente_comprobante(),
            ))
            restante -= monto_cuota

        pagado = self.monto_pagado
        if pagado >= self.monto_total_cuota:
            self.estado_cuota = self.ESTADO_PAGADO
        elif pagado > 0:
            self.estado_cuota = self.ESTADO_PAGADO_PARCIAL
        self.save()

        if restante > 0:
            transacciones_creadas.append(
                self._aplicar_abono_capital(restante, cajero, _siguiente_comprobante())
            )

        if not self.prestamo.cuotas.exclude(estado_cuota=self.ESTADO_PAGADO).exists():
            self.prestamo.transicionar(Prestamo.ESTADO_LIQUIDADO, automatico=True)

        return transacciones_creadas

    def _aplicar_abono_capital(self, monto, cajero, numero_comprobante=''):
        """Registra el exceso pagado como abono a capital y reduce el saldo
        restante del préstamo (de esta cuota en adelante) sin tocar el monto
        de las cuotas futuras."""
        transaccion = TransaccionCaja.objects.create(
            prestamo=self.prestamo, cuota=None, cajero=cajero,
            tipo_movimiento=TransaccionCaja.TIPO_ABONO_CAPITAL,
            monto_pagado=monto,
            numero_comprobante=numero_comprobante,
        )
        cuotas_a_reducir = self.prestamo.cuotas.filter(
            numero_cuota__gte=self.numero_cuota, saldo__gt=0,
        ).order_by('numero_cuota')
        for cuota in cuotas_a_reducir:
            cuota.saldo = max(Decimal('0.00'), cuota.saldo - monto)
            cuota.save(update_fields=['saldo'])
        return transaccion


class TransaccionCaja(models.Model):
    TIPO_PAGO_CUOTA = 'PAGO_CUOTA'
    TIPO_DESEMBOLSO = 'DESEMBOLSO'
    TIPO_AJUSTE = 'AJUSTE'
    TIPO_MORA = 'MORA'
    TIPO_ABONO_CAPITAL = 'ABONO_CAPITAL'

    TIPO_MOVIMIENTO_CHOICES = [
        (TIPO_PAGO_CUOTA, 'Pago de Cuota'),
        (TIPO_DESEMBOLSO, 'Desembolso'),
        (TIPO_AJUSTE, 'Ajuste'),
        (TIPO_MORA, 'Mora'),
        (TIPO_ABONO_CAPITAL, 'Abono a Capital'),
    ]

    prestamo = models.ForeignKey(Prestamo, on_delete=models.PROTECT, related_name='transacciones')
    cuota = models.ForeignKey(
        CuotaAmortizacion, on_delete=models.PROTECT, null=True, blank=True, related_name='transacciones'
    )
    cajero = models.ForeignKey(
        Empleado, on_delete=models.SET_NULL, null=True, blank=True, related_name='transacciones'
    )
    tipo_movimiento = models.CharField(max_length=15, choices=TIPO_MOVIMIENTO_CHOICES)
    monto_pagado = models.DecimalField(max_digits=12, decimal_places=2, validators=[MONTO_POSITIVO])
    fecha_hora = models.DateTimeField(auto_now_add=True)
    numero_comprobante = models.CharField(max_length=30, unique=True, blank=True)

    class Meta:
        verbose_name = 'Transacción de Caja'
        verbose_name_plural = 'Transacciones de Caja'
        ordering = ['-fecha_hora']

    def __str__(self):
        return f'{self.get_tipo_movimiento_display()} - {self.prestamo.codigo_credito} - {self.monto_pagado}'

    def save(self, *args, **kwargs):
        if not self.numero_comprobante:
            self.numero_comprobante = self._generar_numero_comprobante()
        super().save(*args, **kwargs)

    @classmethod
    def _generar_numero_comprobante(cls):
        ultimo_id = (cls.objects.order_by('-id').first().id if cls.objects.exists() else 0) + 1
        return f'TC-{ultimo_id:08d}'
