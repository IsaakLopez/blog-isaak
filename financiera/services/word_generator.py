"""Generación automática de documentos Word (docxtpl) de un Préstamo:
contrato de crédito (con tabla de amortización), solicitud de crédito
(expediente KYC del cliente + datos del préstamo) y recibo de desembolso."""
from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from docx import Document as DocumentoWord
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm
from docxtpl import DocxTemplate

from financiera.models import Cliente, Prestamo
from financiera.services.amortizacion import generar_tabla_amortizacion

TEXTO_FIRMA_SOLICITANTE = 'FIRMA DEL SOLICITANTE'

PLANTILLA_PATH = Path(__file__).resolve().parent.parent / 'templates_docx' / 'contrato_credito.docx'
PLANTILLA_SOLICITUD_PATH = (
    Path(__file__).resolve().parent.parent / 'templates_docx' / 'PLANTILLA_SOLICITUD_DE_CREDITO.docx'
)
PLANTILLA_RECIBO_DESEMBOLSO_PATH = (
    Path(__file__).resolve().parent.parent / 'templates_docx' / 'RECIBO_DE_DESEMBOLSO.docx'
)

_MESES_ES = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
    7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre',
}

# Mapas "valor del modelo -> nombre del checkbox en la plantilla de solicitud".
_DESTINO_A_CHK = {
    Prestamo.DESTINO_MEJORAS: 'chk_destino_mejoras',
    Prestamo.DESTINO_PAGO_DEUDA: 'chk_destino_pago_deuda',
    Prestamo.DESTINO_COLEGIATURA: 'chk_destino_colegiatura',
    Prestamo.DESTINO_GASTOS_MEDICOS: 'chk_destino_gastos_medicos',
    Prestamo.DESTINO_CONSUMO: 'chk_destino_consumo',
}
_TIPO_ID_A_CHK = {
    Cliente.TIPO_ID_IDENTIDAD: 'chk_id_identidad',
    Cliente.TIPO_ID_CARNET_RESIDENCIA: 'chk_id_residencia',
    Cliente.TIPO_ID_PASAPORTE: 'chk_id_pasaporte',
}
_GENERO_A_CHK = {
    Cliente.GENERO_FEMENINO: 'chk_genero_femenino',
    Cliente.GENERO_MASCULINO: 'chk_genero_masculino',
}
_ESTADO_CIVIL_A_CHK = {
    Cliente.ESTADO_CIVIL_SOLTERO: 'chk_civil_soltero',
    Cliente.ESTADO_CIVIL_CASADO: 'chk_civil_casado',
    Cliente.ESTADO_CIVIL_DIVORCIADO: 'chk_civil_divorciado',
    Cliente.ESTADO_CIVIL_UNION_LIBRE: 'chk_civil_union_libre',
}
_TIPO_EMPRESA_A_CHK = {
    Cliente.TIPO_EMPRESA_PRIVADA: 'chk_empresa_privada',
    Cliente.TIPO_EMPRESA_PUBLICA: 'chk_empresa_publica',
    Cliente.TIPO_EMPRESA_ONG: 'chk_empresa_ong',
}
_TIPO_EMPLEADO_A_CHK = {
    Cliente.TIPO_EMPLEADO_INDEPENDIENTE: 'chk_empleado_profesional',
    Cliente.TIPO_EMPLEADO_PROPIETARIO: 'chk_empleado_propietario',
    Cliente.TIPO_EMPLEADO_COMERCIANTE: 'chk_empleado_comerciante',
}
_RANGO_SALARIO_A_CHK = {f'RANGO_{i}': f'chk_salario_{i}' for i in range(1, 8)}

# Placeholders que la plantilla oficial pide pero el sistema todavía no
# recolecta (préstamos con el RAP, parentesco con el patrono, PEP, cuentas
# bancarias) -- se dejan siempre sin marcar (casilla vacía).
_CAMPOS_NO_RECOLECTADOS = {
    'chk_rap_ninguno': ' ☐', 'chk_rap_1': ' ☐', 'chk_rap_2': ' ☐',
    'chk_parentesco_ninguno': ' ☐', 'chk_parentesco_1er': ' ☐', 'chk_parentesco_2do': ' ☐', 'chk_parentesco_3er': ' ☐',
    'parentesco_especifique': '',
    'chk_pep_si': ' ☐', 'chk_pep_no': ' ☐',
    'banco_1': '', 'cuenta_1': '', 'banco_2': '', 'cuenta_2': '',
}


def _con_sangria(contexto, espacios=4):
    """Antepone espacios a cada texto ingresado en la Solicitud de Crédito
    (para que se vea mejor formateado, ej. 'Celular:     90909090'). No
    aplica a las casillas 'chk_*' -- esas ya tienen su propio espaciado,
    calibrado para que la casilla no quede pegada a la opción anterior ni
    provoque saltos de línea en medio de una opción."""
    relleno = ' ' * espacios
    resultado = {}
    for clave, valor in contexto.items():
        if clave.startswith('chk_') or valor in (None, ''):
            resultado[clave] = valor
        else:
            resultado[clave] = f'{relleno}{valor}'
    return resultado


def _marcar(mapa_chk, valor_seleccionado):
    """Devuelve {nombre_chk: ' ☒'/' ☐'}, marcando con una casilla visible la
    opción elegida y dejando las demás como casilla vacía. El espacio inicial
    separa la casilla de la etiqueta ANTERIOR (en la plantilla, cada casilla
    queda pegada al final de la opción previa; sin ese espacio se ve como si
    perteneciera a la opción equivocada)."""
    return {nombre: (' ☒' if clave == valor_seleccionado else ' ☐') for clave, nombre in mapa_chk.items()}


def generar_contrato(prestamo):
    """Rellena la plantilla oficial con los datos del préstamo y la tabla de
    amortización, y guarda el resultado en `prestamo.documento_contrato`."""
    if not PLANTILLA_PATH.exists():
        raise FileNotFoundError(
            'No existe la plantilla de contrato. Ejecuta '
            '"python manage.py generar_plantilla_contrato" primero.'
        )

    tabla = generar_tabla_amortizacion(
        monto=prestamo.monto_solicitado,
        tasa_interes_anual=prestamo.tasa_interes_anual,
        plazo_meses=prestamo.plazo_meses,
        frecuencia_pago=prestamo.frecuencia_pago,
        fecha_inicio=prestamo.fecha_solicitud.date(),
    )

    cliente = prestamo.cliente
    contexto = {
        'codigo_credito': prestamo.codigo_credito,
        'fecha_aprobacion': prestamo.fecha_aprobacion.strftime('%d/%m/%Y') if prestamo.fecha_aprobacion else '',
        'cliente_nombre': cliente.nombre_completo,
        'cliente_dni': cliente.numero_identificacion,
        'cliente_direccion': cliente.direccion_completa or 'No registrada',
        'monto_solicitado': f'L {prestamo.monto_solicitado:,.2f}',
        'tasa_interes_anual': prestamo.tasa_interes_anual,
        'plazo_meses': prestamo.plazo_meses,
        'frecuencia_pago': prestamo.get_frecuencia_pago_display(),
        'numero_cuotas': len(tabla),
        'cuotas': [
            {
                'numero_cuota': cuota['numero_cuota'],
                'fecha_vencimiento': cuota['fecha_vencimiento'].strftime('%d/%m/%Y'),
                'monto_capital': f"L {cuota['monto_capital']:,.2f}",
                'monto_interes': f"L {cuota['monto_interes']:,.2f}",
                'monto_total_cuota': f"L {cuota['monto_total_cuota']:,.2f}",
            }
            for cuota in tabla
        ],
    }

    documento = DocxTemplate(str(PLANTILLA_PATH))
    documento.render(contexto)

    buffer = BytesIO()
    documento.save(buffer)
    buffer.seek(0)

    nombre_archivo = f'{prestamo.codigo_credito}.docx'
    prestamo.documento_contrato.save(nombre_archivo, ContentFile(buffer.read()), save=True)
    return prestamo.documento_contrato


def _insertar_firma_digital(buffer_docx, imagen_firma):
    """Abre el .docx ya renderizado e inserta la imagen de la firma (PNG con
    fondo transparente) en un párrafo nuevo, justo encima del texto "FIRMA
    DEL SOLICITANTE". La celda de la tabla donde vive ese texto está
    fusionada a lo ancho de toda la fila, así que `fila.cells` repite la
    misma celda una vez por columna cubierta -- se descartan los duplicados
    con `vistas` para no insertar la imagen varias veces."""
    documento = DocumentoWord(buffer_docx)
    # OJO: se descarta por el elemento `_tc` en sí, no por id(_tc) -- lxml crea
    # un proxy Python efímero en cada acceso, así que id(_tc) puede reciclarse
    # entre columnas distintas y romper el descarte de duplicados.
    vistas = set()
    for tabla in documento.tables:
        for fila in tabla.rows:
            for celda in fila.cells:
                if celda._tc in vistas:
                    continue
                vistas.add(celda._tc)
                for parrafo in celda.paragraphs:
                    if parrafo.text.strip().upper() == TEXTO_FIRMA_SOLICITANTE:
                        nuevo_parrafo = parrafo.insert_paragraph_before()
                        nuevo_parrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        nuevo_parrafo.add_run().add_picture(imagen_firma, height=Cm(2.2))

    salida = BytesIO()
    documento.save(salida)
    salida.seek(0)
    return salida


def generar_solicitud_credito(prestamo, imagen_firma=None):
    """Rellena la plantilla oficial de Solicitud de Crédito con los datos del
    préstamo y el expediente KYC del cliente. Devuelve un BytesIO listo para
    descargar (no se persiste en el modelo, se genera al vuelo).

    `imagen_firma` (BytesIO opcional) es la imagen de firma digital ya
    procesada (fondo blanco eliminado); si se recibe, se inserta sobre el
    texto "FIRMA DEL SOLICITANTE". Si es None, la solicitud se genera igual
    que antes, para que el firmante la imprima y la firme a mano."""
    if not PLANTILLA_SOLICITUD_PATH.exists():
        raise FileNotFoundError('No existe la plantilla de solicitud de crédito.')

    cliente = prestamo.cliente
    contexto = {
        # Datos del crédito
        'plazo': prestamo.plazo_meses,
        'monto_solicitado': f'L {prestamo.monto_solicitado:,.2f}',
        'fecha_solicitud': prestamo.fecha_solicitud.strftime('%d/%m/%Y'),
        **_marcar(_DESTINO_A_CHK, prestamo.destino),

        # 1. Identificación personal
        'primer_nombre': cliente.primer_nombre,
        'segundo_nombre': cliente.segundo_nombre,
        'primer_apellido': cliente.primer_apellido,
        'segundo_apellido': cliente.segundo_apellido,
        'fecha_nacimiento': cliente.fecha_nacimiento.strftime('%d/%m/%Y'),
        'lugar_nacimiento': cliente.lugar_nacimiento,
        'numero_identificacion': cliente.numero_identificacion,
        'nacionalidad': cliente.get_nacionalidad_display(),
        'profesion': cliente.profesion_ocupacion_oficio,
        **_marcar(_TIPO_ID_A_CHK, cliente.tipo_identificacion),
        **_marcar(_GENERO_A_CHK, cliente.genero),

        # 2. Contacto y domicilio
        'telefono_fijo': cliente.telefono_fijo,
        'celular': cliente.celular,
        'email_personal': cliente.email_personal,
        'direccion_domicilio': cliente.direccion_colonia_barrio,
        'calle_avenida': cliente.calle_avenida,
        'numero_casa': cliente.numero_casa,
        'punto_referencia': cliente.punto_referencia,
        'municipio': cliente.municipio,
        'departamento': cliente.departamento,
        'pais': cliente.pais,

        # 3. Estado civil y familia
        'numero_dependientes': cliente.numero_dependientes,
        'conyuge_nombre': cliente.nombre_conyuge,
        'conyuge_telefono_fijo': cliente.conyuge_telefono_fijo,
        'conyuge_celular': cliente.conyuge_celular,
        'conyuge_empresa': cliente.conyuge_empresa,
        **_marcar(_ESTADO_CIVIL_A_CHK, cliente.estado_civil),

        # 4. Referencias personales
        'referencia1_nombre': cliente.ref1_nombre,
        'referencia1_telefono_fijo': cliente.ref1_telefono_fijo,
        'referencia1_celular': cliente.ref1_celular,
        'referencia2_nombre': cliente.ref2_nombre,
        'referencia2_telefono_fijo': cliente.ref2_telefono_fijo,
        'referencia2_celular': cliente.ref2_celular,

        # 5. Información profesional y laboral
        'empresa_nombre': cliente.empresa_nombre,
        'fecha_ingreso': cliente.empresa_fecha_ingreso.strftime('%d/%m/%Y'),
        'anios_laborando': cliente.empresa_anios_laborando,
        'cargo_actual': cliente.cargo_actual,
        'empresa_telefono': cliente.empresa_telefono,
        'email_laboral': cliente.empresa_email,
        'empresa_direccion': cliente.empresa_direccion,
        'empresa_ciudad': cliente.empresa_ciudad,
        'empresa_municipio': cliente.empresa_municipio,
        'empresa_departamento': cliente.empresa_departamento,
        'nombre_gerente_rrhh': cliente.gerente_rrhh_nombre,
        'nombre_jefe_inmediato': cliente.jefe_inmediato_nombre,
        **_marcar(_TIPO_EMPRESA_A_CHK, cliente.tipo_empresa),
        **_marcar(_TIPO_EMPLEADO_A_CHK, cliente.tipo_empleado),

        # 6. Información financiera — el ingreso mensual ya no se recolecta en el
        # formulario, así que se deja en blanco en vez de imprimir un falso "L 0.00".
        'ingreso_mensual': '',
        **_marcar(_RANGO_SALARIO_A_CHK, cliente.rango_salario),

        # Ciudad donde se firma: siempre la sede de la institución, no depende
        # del cliente.
        'ciudad_firma': 'El Rosario, Comayagua',

        **_CAMPOS_NO_RECOLECTADOS,
    }
    contexto = _con_sangria(contexto)

    documento = DocxTemplate(str(PLANTILLA_SOLICITUD_PATH))
    documento.render(contexto)

    buffer = BytesIO()
    documento.save(buffer)
    buffer.seek(0)

    if imagen_firma is not None:
        buffer = _insertar_firma_digital(buffer, imagen_firma)

    return buffer


def generar_recibo_desembolso(prestamo):
    """Rellena la plantilla oficial de Recibo de Desembolso con los datos
    del préstamo ya desembolsado. Devuelve un BytesIO listo para descargar
    (no se persiste en el modelo, se genera al vuelo)."""
    if not PLANTILLA_RECIBO_DESEMBOLSO_PATH.exists():
        raise FileNotFoundError('No existe la plantilla de recibo de desembolso.')
    if not prestamo.fecha_desembolso:
        raise ValueError('El préstamo todavía no ha sido desembolsado.')

    fecha = prestamo.fecha_desembolso
    contexto = {
        'cliente_nombre': prestamo.cliente.nombre_completo,
        'cliente_dni': prestamo.cliente.numero_identificacion,
        'monto_desembolsado': f'{prestamo.monto_solicitado:,.2f}',
        'dia_desembolso': fecha.day,
        'mes_desembolso': _MESES_ES[fecha.month],
        'anio_desembolso': fecha.year,
    }

    documento = DocxTemplate(str(PLANTILLA_RECIBO_DESEMBOLSO_PATH))
    documento.render(contexto)

    buffer = BytesIO()
    documento.save(buffer)
    buffer.seek(0)
    return buffer
