"""Conversión de un monto en Lempiras a su representación en letras
(ej. Decimal('25000.00') -> 'VEINTICINCO MIL LEMPIRAS EXACTOS'), como exige
el formato tradicional de un pagaré para que el monto no pueda alterarse."""
from decimal import Decimal, ROUND_HALF_UP

_UNIDADES = ['', 'UNO', 'DOS', 'TRES', 'CUATRO', 'CINCO', 'SEIS', 'SIETE', 'OCHO', 'NUEVE']
_DIECI = [
    'DIEZ', 'ONCE', 'DOCE', 'TRECE', 'CATORCE', 'QUINCE',
    'DIECISÉIS', 'DIECISIETE', 'DIECIOCHO', 'DIECINUEVE',
]
_VEINTI = [
    'VEINTE', 'VEINTIUNO', 'VEINTIDÓS', 'VEINTITRÉS', 'VEINTICUATRO',
    'VEINTICINCO', 'VEINTISÉIS', 'VEINTISIETE', 'VEINTIOCHO', 'VEINTINUEVE',
]
_DECENAS = ['', '', '', 'TREINTA', 'CUARENTA', 'CINCUENTA', 'SESENTA', 'SETENTA', 'OCHENTA', 'NOVENTA']
_CENTENAS = [
    '', 'CIENTO', 'DOSCIENTOS', 'TRESCIENTOS', 'CUATROCIENTOS', 'QUINIENTOS',
    'SEISCIENTOS', 'SETECIENTOS', 'OCHOCIENTOS', 'NOVECIENTOS',
]

# Apocope de "uno" ante un sustantivo (VEINTIUNO -> VEINTIÚN, UNO -> UN, etc.),
# ordenado del sufijo más largo al más corto para no recortar de más.
_SUFIJOS_UNO_A_UN = [
    ('VEINTIUNO', 'VEINTIÚN'),
    ('TREINTA Y UNO', 'TREINTA Y UN'),
    ('CUARENTA Y UNO', 'CUARENTA Y UN'),
    ('CINCUENTA Y UNO', 'CINCUENTA Y UN'),
    ('SESENTA Y UNO', 'SESENTA Y UN'),
    ('SETENTA Y UNO', 'SETENTA Y UN'),
    ('OCHENTA Y UNO', 'OCHENTA Y UN'),
    ('NOVENTA Y UNO', 'NOVENTA Y UN'),
    ('UNO', 'UN'),
]


def _apocopar(texto):
    for sufijo_uno, sufijo_un in _SUFIJOS_UNO_A_UN:
        if texto.endswith(sufijo_uno):
            return texto[:-len(sufijo_uno)] + sufijo_un
    return texto


def _decenas_a_letras(n):
    """n en [1, 99]."""
    if n < 10:
        return _UNIDADES[n]
    if n < 20:
        return _DIECI[n - 10]
    if n < 30:
        return _VEINTI[n - 20]
    decena, unidad = divmod(n, 10)
    if unidad == 0:
        return _DECENAS[decena]
    return f'{_DECENAS[decena]} Y {_UNIDADES[unidad]}'


def _centenas_a_letras(n):
    """n en [1, 999]."""
    if n == 100:
        return 'CIEN'
    centena, resto = divmod(n, 100)
    partes = []
    if centena:
        partes.append(_CENTENAS[centena])
    if resto:
        partes.append(_decenas_a_letras(resto))
    return ' '.join(partes)


def numero_a_letras(numero):
    """Convierte un entero no negativo a su representación en letras en
    español (sin apocopar el final -- eso lo decide quien lo use según el
    sustantivo que sigue, ej. `_apocopar(...)` antes de "LEMPIRAS")."""
    numero = int(numero)
    if numero == 0:
        return 'CERO'

    millones, resto = divmod(numero, 1_000_000)
    miles, unidades = divmod(resto, 1000)

    partes = []
    if millones:
        if millones == 1:
            partes.append('UN MILLÓN')
        else:
            partes.append(f'{_apocopar(_centenas_a_letras(millones))} MILLONES')
    if miles:
        if miles == 1:
            partes.append('MIL')
        else:
            partes.append(f'{_apocopar(_centenas_a_letras(miles))} MIL')
    if unidades:
        partes.append(_centenas_a_letras(unidades))

    return ' '.join(partes)


def monto_en_letras(valor):
    """Convierte un monto en Lempiras (Decimal/float/str) a su
    representación legal en letras, ej.:
    Decimal('25000.00') -> 'VEINTICINCO MIL LEMPIRAS EXACTOS'
    Decimal('1250.50')  -> 'MIL DOSCIENTOS CINCUENTA LEMPIRAS CON 50/100'
    """
    valor = Decimal(valor).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    entero = int(valor)
    centavos = int((valor - entero) * 100)

    letras_entero = _apocopar(numero_a_letras(entero))
    moneda = 'LEMPIRA' if entero == 1 else 'LEMPIRAS'

    if centavos:
        return f'{letras_entero} {moneda} CON {centavos:02d}/100'
    exactos = 'EXACTO' if entero == 1 else 'EXACTOS'
    return f'{letras_entero} {moneda} {exactos}'
