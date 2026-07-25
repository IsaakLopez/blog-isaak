"""Cálculo de la tabla de amortización (sistema francés de cuota fija)."""
import calendar
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

DOS_DECIMALES = Decimal('0.01')

# Días fijos entre pagos para las frecuencias que NO son mensuales (semanal
# y quincenal sí caen cada 7/15 días exactos). La mensual se calcula sumando
# meses de calendario (ver `_sumar_meses`), no 30 días fijos, para que el
# pago caiga siempre en el mismo día del mes en que se desembolsó (ej. si
# se desembolsa el 24, todas las cuotas vencen el día 24 de cada mes).
FRECUENCIA_A_DIAS = {
    'SEMANAL': 7,
    'QUINCENAL': 15,
}

FRECUENCIA_A_PAGOS_POR_ANIO = {
    'SEMANAL': Decimal('52'),
    'QUINCENAL': Decimal('24'),
    'MENSUAL': Decimal('12'),
}


def _redondear(valor):
    return Decimal(valor).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)


def _sumar_meses(fecha, meses):
    """Suma `meses` meses de calendario a `fecha`, conservando el mismo día
    del mes siempre que exista en el mes destino (ej. 31 de enero + 1 mes =
    28/29 de febrero, no el 3 de marzo)."""
    mes_total = fecha.month - 1 + meses
    anio = fecha.year + mes_total // 12
    mes = mes_total % 12 + 1
    dia = min(fecha.day, calendar.monthrange(anio, mes)[1])
    return fecha.replace(year=anio, month=mes, day=dia)


def _fecha_cuota(fecha_inicio, numero, frecuencia_pago):
    if frecuencia_pago == 'MENSUAL':
        return _sumar_meses(fecha_inicio, numero)
    return fecha_inicio + timedelta(days=FRECUENCIA_A_DIAS[frecuencia_pago] * numero)


def _numero_de_cuotas(plazo_meses, frecuencia_pago):
    pagos_por_anio = FRECUENCIA_A_PAGOS_POR_ANIO[frecuencia_pago]
    return int((Decimal(plazo_meses) / Decimal('12') * pagos_por_anio).to_integral_value(rounding=ROUND_HALF_UP))


def generar_tabla_amortizacion(monto, tasa_interes_anual, plazo_meses, frecuencia_pago, fecha_inicio):
    """Devuelve una lista de dicts listos para crear objetos CuotaAmortizacion,
    usando el sistema francés de cuota fija. El redondeo se ajusta en la
    última cuota para que la suma de capital cuadre exactamente con el monto
    solicitado."""
    monto = Decimal(monto)
    tasa_anual = Decimal(tasa_interes_anual) / Decimal('100')
    numero_cuotas = _numero_de_cuotas(plazo_meses, frecuencia_pago)
    pagos_por_anio = FRECUENCIA_A_PAGOS_POR_ANIO[frecuencia_pago]

    tasa_periodica = tasa_anual / pagos_por_anio

    if tasa_periodica == 0:
        cuota_fija = _redondear(monto / numero_cuotas)
    else:
        factor = (1 + tasa_periodica) ** numero_cuotas
        cuota_fija = _redondear(monto * (tasa_periodica * factor) / (factor - 1))

    saldo = monto
    tabla = []
    for numero in range(1, numero_cuotas + 1):
        interes = _redondear(saldo * tasa_periodica)
        capital = cuota_fija - interes

        if numero == numero_cuotas:
            # Ajuste de redondeo: la última cuota salda exactamente el saldo restante.
            capital = saldo
            cuota_total = capital + interes
        else:
            cuota_total = cuota_fija

        saldo -= capital
        tabla.append({
            'numero_cuota': numero,
            'fecha_vencimiento': _fecha_cuota(fecha_inicio, numero, frecuencia_pago),
            'monto_capital': capital,
            'monto_interes': interes,
            'monto_total_cuota': cuota_total,
            'saldo': saldo,
        })

    return tabla
