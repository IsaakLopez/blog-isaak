"""Limpieza de la imagen de firma digital: quita el fondo (blanco, gris,
amarillento, con sombras o iluminación despareja) y recorta los márgenes
transparentes sobrantes. El archivo ya llega validado como imagen por
`FirmaSolicitudForm` (ImageField).

En vez de comparar cada pixel contra un blanco fijo (255,255,255) -- lo cual
falla apenas la foto tiene una sombra o el papel no es perfectamente
blanco -- se estima el fondo de forma LOCAL: un desenfoque grande sobre la
imagen en escala de grises borra el trazo fino de la tinta pero conserva el
tono y la iluminación del papel en cada zona. Comparando cada pixel contra
ese fondo estimado en su propia zona (no un valor global), la tinta se
detecta igual de bien esté el fondo blanco, gris, crema o con un degradado
de luz de un lado a otro."""
from io import BytesIO

from PIL import Image, ImageChops, ImageFilter

# Diferencia de brillo (0-255) entre un pixel y el fondo estimado en su
# zona: por debajo de DIFERENCIA_RUIDO se considera textura/ruido del papel
# (transparente); por encima de DIFERENCIA_TINTA se considera trazo de tinta
# (opaco); entre ambos se interpola para suavizar el borde.
DIFERENCIA_RUIDO = 10
DIFERENCIA_TINTA = 45

# La firma se inserta en el documento a un tamaño pequeño (unos 2 cm de
# alto), así que no hace falta procesar la imagen a su resolución original
# -- limitar el tamaño mantiene la limpieza del fondo rápida incluso con
# fotos de celular de varios megapixeles.
TAMANO_MAXIMO = (1600, 1600)


def _tabla_alfa_por_diferencia():
    tabla = []
    for diferencia in range(256):
        if diferencia <= DIFERENCIA_RUIDO:
            tabla.append(0)
        elif diferencia >= DIFERENCIA_TINTA:
            tabla.append(255)
        else:
            tabla.append(round(255 * (diferencia - DIFERENCIA_RUIDO) / (DIFERENCIA_TINTA - DIFERENCIA_RUIDO)))
    return tabla


def limpiar_firma_digital(archivo):
    """Recibe el archivo subido (firma escrita sobre un fondo claro) y
    devuelve un BytesIO en PNG con canal alfa transparente, listo para
    insertar en el documento Word."""
    archivo.seek(0)
    imagen = Image.open(archivo)
    imagen.load()
    imagen = imagen.convert('RGBA')
    imagen.thumbnail(TAMANO_MAXIMO, Image.LANCZOS)

    gris = imagen.convert('L')
    # Radio proporcional al tamaño de la imagen: debe ser mucho más ancho
    # que el trazo de la tinta para que el desenfoque lo borre por completo
    # y deje solo el fondo estimado.
    radio_desenfoque = max(12, min(imagen.size) // 12)
    fondo_estimado = gris.filter(ImageFilter.GaussianBlur(radio_desenfoque))
    diferencia = ImageChops.subtract(fondo_estimado, gris)

    canal_alfa = diferencia.point(_tabla_alfa_por_diferencia())
    # Filtro de mediana: borra pixeles sueltos que el ruido de una foto con
    # poca luz puede colar por encima del umbral; el trazo real es una zona
    # continua, no puntos aislados, así que no se ve afectado.
    canal_alfa = canal_alfa.filter(ImageFilter.MedianFilter(size=3))
    imagen.putalpha(canal_alfa)

    caja = imagen.getbbox()
    if caja:
        imagen = imagen.crop(caja)

    salida = BytesIO()
    imagen.save(salida, format='PNG')
    salida.seek(0)
    return salida
