"""Cálculo de la tabla de amortización (sistema francés de cuota fija)."""
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

DOS_DECIMALES = Decimal('0.01')

FRECUENCIA_A_DIAS = {
    'SEMANAL': 7,
    'QUINCENAL': 15,
    'MENSUAL': 30,
}

FRECUENCIA_A_PAGOS_POR_ANIO = {
    'SEMANAL': Decimal('52'),
    'QUINCENAL': Decimal('24'),
    'MENSUAL': Decimal('12'),
}


def _redondear(valor):
    return Decimal(valor).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)


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
    dias_periodo = FRECUENCIA_A_DIAS[frecuencia_pago]

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
            'fecha_vencimiento': fecha_inicio + timedelta(days=dias_periodo * numero),
            'monto_capital': capital,
            'monto_interes': interes,
            'monto_total_cuota': cuota_total,
        })

    return tabla
