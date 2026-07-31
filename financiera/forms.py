from decimal import Decimal

from django import forms
from django.utils import timezone

from .models import Cliente, Prestamo

FECHA_WIDGET = forms.DateInput(attrs={'type': 'date'})

# Campos de radio-button cuyas choices vienen directo del modelo, sin la
# opción en blanco que Django agrega automáticamente a los CharField con
# choices que no tienen un default.
CAMPOS_RADIO = [
    'tipo_identificacion', 'genero', 'estado_civil', 'tipo_empresa', 'tipo_empleado', 'rango_salario',
]


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            # 1. Datos de identificación personal
            'primer_nombre', 'segundo_nombre', 'primer_apellido', 'segundo_apellido',
            'fecha_nacimiento', 'lugar_nacimiento', 'tipo_identificacion', 'numero_identificacion',
            'genero', 'nacionalidad', 'profesion_ocupacion_oficio',
            # 2. Información de contacto y domicilio
            'telefono_fijo', 'celular', 'email_personal', 'direccion_colonia_barrio',
            'calle_avenida', 'numero_casa', 'punto_referencia', 'municipio', 'departamento', 'pais',
            # 3. Estado civil y datos familiares
            'estado_civil', 'numero_dependientes', 'nombre_conyuge',
            'conyuge_telefono_fijo', 'conyuge_celular', 'conyuge_empresa',
            # 4. Referencias personales
            'ref1_nombre', 'ref1_telefono_fijo', 'ref1_celular',
            'ref2_nombre', 'ref2_telefono_fijo', 'ref2_celular',
            # 5. Información profesional y laboral
            'tipo_empresa', 'tipo_empleado', 'empresa_nombre', 'empresa_fecha_ingreso',
            'empresa_anios_laborando', 'cargo_actual', 'empresa_telefono', 'empresa_email',
            'empresa_direccion', 'empresa_ciudad', 'empresa_municipio', 'empresa_departamento',
            'gerente_rrhh_nombre', 'jefe_inmediato_nombre', 'rango_salario',
        ]
        widgets = {
            'fecha_nacimiento': FECHA_WIDGET,
            'empresa_fecha_ingreso': FECHA_WIDGET,
            'tipo_identificacion': forms.RadioSelect,
            'genero': forms.RadioSelect,
            'estado_civil': forms.RadioSelect,
            'tipo_empresa': forms.RadioSelect,
            'tipo_empleado': forms.RadioSelect,
            'rango_salario': forms.RadioSelect,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nombre_campo in CAMPOS_RADIO:
            self.fields[nombre_campo].choices = getattr(Cliente, f'{nombre_campo.upper()}_CHOICES')


# Tasas fijas que la institución maneja hoy; se muestran como lista para
# evitar que se ingresen valores fuera de lo permitido.
TASA_INTERES_CHOICES = [
    ('5', '5%'),
    ('4.5', '4.5%'),
    ('4', '4%'),
    ('3.5', '3.5%'),
    ('3', '3%'),
]


class PrestamoForm(forms.ModelForm):
    numero_identificacion_cliente = forms.CharField(
        label='No. de Identificación del Cliente', max_length=20,
        help_text='Ingresa el número de identificación (DNI) del cliente ya registrado en el sistema.',
    )

    class Meta:
        model = Prestamo
        fields = ['monto_solicitado', 'tasa_interes_mensual', 'plazo_meses', 'frecuencia_pago', 'tipo_credito', 'destino']
        widgets = {
            'destino': forms.RadioSelect,
            'tipo_credito': forms.RadioSelect,
            'tasa_interes_mensual': forms.Select(choices=TASA_INTERES_CHOICES),
        }

    field_order = [
        'numero_identificacion_cliente', 'monto_solicitado', 'tasa_interes_mensual',
        'plazo_meses', 'frecuencia_pago', 'tipo_credito', 'destino',
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['destino'].choices = Prestamo.DESTINO_CHOICES
        self.fields['tipo_credito'].choices = Prestamo.TIPO_CREDITO_CHOICES
        self.order_fields(self.field_order)

    def clean_numero_identificacion_cliente(self):
        numero = self.cleaned_data['numero_identificacion_cliente'].strip()
        try:
            self.cliente_encontrado = Cliente.objects.get(numero_identificacion=numero)
        except Cliente.DoesNotExist:
            raise forms.ValidationError(
                'No existe ningún cliente registrado con ese número de identificación. '
                'Verifícalo o regístralo primero en el módulo de Clientes.'
            )
        return numero

    def save(self, commit=True):
        prestamo = super().save(commit=False)
        prestamo.cliente = self.cliente_encontrado
        if commit:
            prestamo.save()
        return prestamo


class PagoCuotaForm(forms.Form):
    monto = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=0.01, label='Monto a pagar',
        help_text='Puede ser menor a la cuota (abono parcial) o mayor (el exceso se abona a capital).',
    )
    numero_comprobante = forms.CharField(max_length=30, required=False, label='N° de comprobante externo (opcional)')


class FirmaDocumentoForm(forms.Form):
    """Elección de firma manual/digital al generar la Solicitud de Crédito,
    el Recibo de Desembolso o el Pagaré."""
    TIPO_FIRMA_MANUAL = 'manual'
    TIPO_FIRMA_DIGITAL = 'digital'
    TIPO_FIRMA_CHOICES = [
        (TIPO_FIRMA_MANUAL, 'Firma manual'),
        (TIPO_FIRMA_DIGITAL, 'Firma digital'),
    ]

    tipo_firma = forms.ChoiceField(
        choices=TIPO_FIRMA_CHOICES, widget=forms.RadioSelect, initial=TIPO_FIRMA_MANUAL,
    )
    firma_imagen = forms.ImageField(
        required=False, label='Imagen de la firma (fondo blanco)',
        error_messages={'invalid_image': 'El archivo no es una imagen válida.'},
    )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('tipo_firma') == self.TIPO_FIRMA_DIGITAL and not cleaned_data.get('firma_imagen'):
            self.add_error('firma_imagen', 'Debes subir una imagen de la firma para la firma digital.')
        return cleaned_data


# --- Asistente de migración de créditos históricos (solo Gerente/Admin) ---

class MigracionPaso1Form(forms.Form):
    """Datos del crédito histórico a migrar. El cliente debe existir ya en
    el sistema (se registra por el flujo normal de Clientes) -- aquí solo
    se busca por DNI, igual que en `PrestamoForm`."""
    numero_identificacion_cliente = forms.CharField(
        label='No. de Identificación del Cliente', max_length=20,
        help_text='El cliente debe estar registrado ya en el sistema.',
    )
    monto_solicitado = forms.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'), label='Monto del Crédito')
    tasa_interes_mensual = forms.ChoiceField(choices=TASA_INTERES_CHOICES, label='Tasa de Interés Mensual (%)')
    plazo_meses = forms.IntegerField(min_value=1, label='Plazo (meses)')
    frecuencia_pago = forms.ChoiceField(choices=Prestamo.FRECUENCIA_CHOICES, label='Frecuencia de Pago')
    tipo_credito = forms.ChoiceField(choices=Prestamo.TIPO_CREDITO_CHOICES, label='Tipo de Crédito')
    destino = forms.ChoiceField(choices=Prestamo.DESTINO_CHOICES, label='Destino del Préstamo')
    fecha_inicio = forms.DateField(
        widget=FECHA_WIDGET, label='Fecha de inicio (desembolso real del crédito)',
        help_text='La fecha real en que se entregó el dinero, no la fecha de hoy.',
    )

    def clean_numero_identificacion_cliente(self):
        numero = self.cleaned_data['numero_identificacion_cliente'].strip()
        try:
            self.cliente_encontrado = Cliente.objects.get(numero_identificacion=numero)
        except Cliente.DoesNotExist:
            raise forms.ValidationError(
                'No existe ningún cliente registrado con ese número de identificación. '
                'Regístralo primero en el módulo de Clientes.'
            )
        return numero

    def clean_fecha_inicio(self):
        fecha = self.cleaned_data['fecha_inicio']
        if fecha > timezone.localdate():
            raise forms.ValidationError('La fecha de inicio no puede ser en el futuro.')
        return fecha


class MigracionPaso2Form(forms.Form):
    cuotas_pagadas = forms.IntegerField(
        min_value=0, label='¿Cuántas cuotas ya están pagadas?',
        help_text='Puedes dejarlo en 0 si el crédito no tiene ningún pago todavía.',
    )

    def __init__(self, *args, total_cuotas, **kwargs):
        self.total_cuotas = total_cuotas
        super().__init__(*args, **kwargs)
        self.fields['cuotas_pagadas'].help_text += f' Este crédito tiene {total_cuotas} cuotas en total.'

    def clean_cuotas_pagadas(self):
        cantidad = self.cleaned_data['cuotas_pagadas']
        if cantidad > self.total_cuotas:
            raise forms.ValidationError(f'El crédito solo tiene {self.total_cuotas} cuotas en total.')
        return cantidad


class MigracionPaso3Form(forms.Form):
    """Una fecha y un monto por cada cuota ya pagada, precargados con lo
    programado pero editables (para reflejar pagos parciales o con mora que
    ya se cobró en su momento). Campos dinámicos: `fecha_1`/`monto_1`,
    `fecha_2`/`monto_2`, ... según `cuotas_a_migrar`."""

    def __init__(self, *args, cuotas_a_migrar, **kwargs):
        """`cuotas_a_migrar`: lista de dicts con 'numero_cuota', 'fecha_vencimiento'
        (date) y 'monto_total_cuota' (Decimal), en orden."""
        self.cuotas_a_migrar = cuotas_a_migrar
        super().__init__(*args, **kwargs)
        for cuota in cuotas_a_migrar:
            numero = cuota['numero_cuota']
            self.fields[f'fecha_{numero}'] = forms.DateField(
                widget=FECHA_WIDGET, label=f'Cuota {numero} — fecha de pago',
                initial=cuota['fecha_vencimiento'],
            )
            self.fields[f'monto_{numero}'] = forms.DecimalField(
                max_digits=12, decimal_places=2, min_value=Decimal('0.01'),
                label=f'Cuota {numero} — monto pagado',
                initial=cuota['monto_total_cuota'],
            )

    def clean(self):
        cleaned_data = super().clean()
        hoy = timezone.localdate()
        for cuota in self.cuotas_a_migrar:
            numero = cuota['numero_cuota']
            fecha = cleaned_data.get(f'fecha_{numero}')
            if fecha and fecha > hoy:
                self.add_error(f'fecha_{numero}', 'No puede ser una fecha futura.')
        return cleaned_data

    def obtener_pagos_migrados(self):
        """Devuelve la lista de (numero_cuota, fecha_pago, monto) lista para
        pasarle a `migrar_credito`, en orden de numero_cuota."""
        pagos = []
        for cuota in self.cuotas_a_migrar:
            numero = cuota['numero_cuota']
            pagos.append((
                numero,
                self.cleaned_data[f'fecha_{numero}'],
                self.cleaned_data[f'monto_{numero}'],
            ))
        return pagos
