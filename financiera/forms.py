from django import forms

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
            'gerente_rrhh_nombre', 'jefe_inmediato_nombre',
            # 6. Información financiera
            'actividad_economica', 'ingresos_mensuales', 'rango_salario',
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


class PrestamoForm(forms.ModelForm):
    class Meta:
        model = Prestamo
        fields = ['cliente', 'monto_solicitado', 'tasa_interes_anual', 'plazo_meses', 'frecuencia_pago']


class PagoCuotaForm(forms.Form):
    monto = forms.DecimalField(max_digits=12, decimal_places=2, min_value=0.01, label='Monto a pagar')
    numero_comprobante = forms.CharField(max_length=30, required=False, label='N° de comprobante externo (opcional)')
