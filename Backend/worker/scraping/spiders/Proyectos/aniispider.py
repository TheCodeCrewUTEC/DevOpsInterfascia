import json
import re
import scrapy

# El listado de https://anii.org.uy/proyectos/ se carga por AJAX desde este endpoint
AJAX_PROYECTOS = 'https://anii.org.uy/app/ajax/frontend/getMoreProjects.php'
POR_PAGINA = 100

# Etiquetas de la ficha del proyecto -> clave en el item
CAMPOS = {
    'INSTRUMENTO': 'instrumento',
    'ÁREA DE PROY.': 'area_proyecto',
    'SECTOR': 'sector',
    'BENEFICIARIO': 'beneficiario',
    'SUBSIDIO': 'subsidio',
    'FECHA DE INICIO': 'fecha_inicio',
    'DURACIÓN': 'duracion',
    'AÑO CONVOCATORIA': 'anio_convocatoria',
    'CÓDIGO': 'codigo',
    'FASE': 'fase',
    'ESTADO': 'estado',
}

RESUMENES = {
    'RESUMEN PUBLICABLE INICIAL': 'resumen_inicial',
    'RESUMEN PUBLICABLE FINAL': 'resumen_final',
}


def limpiar(texto):
    return re.sub(r'\s+', ' ', texto or '').strip()


class  AniiSpyder(scrapy.Spider):
    name = 'ProyectoAnii'

    custom_settings = {
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'AUTOTHROTTLE_ENABLED': True,
        'DOWNLOAD_TIMEOUT': 120,
        'FEED_EXPORT_ENCODING': 'utf-8',
    }

    # Por defecto solo proyectos ya realizados (fase CERRADO / estado Terminado).
    # Pasar fase= o estado= vacíos para traer todos.
    def __init__(self, fase='CERRADO', estado='Terminado', limit=0, solo_listado=0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fase = fase
        self.estado = estado
        self.limit = int(limit)
        self.solo_listado = bool(int(solo_listado))

    async def start(self):
        yield self.pedir_pagina(0)

    def pedir_pagina(self, offset):
        count = POR_PAGINA
        if self.limit:
            count = min(count, self.limit - offset)
        return scrapy.FormRequest(
            AJAX_PROYECTOS,
            formdata={
                'offset': str(offset),
                'count': str(count),
                'order': 'anioconvocatoria',
                'criteria': 'DESC',
                'qry': '',
                'fase': self.fase,
                'estado': self.estado,
            },
            callback=self.parse,
            cb_kwargs={'offset': offset},
        )

    # listado de proyectos (filas de la tabla que devuelve el AJAX)
    def parse(self, response, offset):
        datos = json.loads(response.text)
        filas = scrapy.Selector(text=datos.get('html') or '').css('tr')

        for Proyecto in filas:
            celdas = [limpiar(' '.join(td.css('::text').getall())) for td in Proyecto.css('td')]
            if len(celdas) < 5:
                continue
            fase, _, estado = celdas[3].partition('/')
            proyecto = {
                'titulo': celdas[0],
                'beneficiario': celdas[1],
                'area': celdas[2],
                'fase': fase.strip(),
                'estado': estado.strip(),
                'anio_convocatoria': celdas[4],
                'link': Proyecto.css('a::attr(href)').get(),
            }
            if self.solo_listado:
                yield proyecto
                continue

            # la ficha redirige (301) a la misma URL con "/" final; se pide directo
            yield scrapy.Request(
                proyecto['link'].rstrip('/') + '/',
                callback=self.parse_proyecto,
                cb_kwargs={'proyecto': proyecto}
            )

        siguiente = offset + len(filas)
        total = int(datos.get('total') or 0)
        if self.limit:
            total = min(total, self.limit)
        if filas and siguiente < total:
            yield self.pedir_pagina(siguiente)

    # ficha de cada proyecto
    def parse_proyecto(self, response, proyecto):
        # el titulo del listado viene truncado ("..."), el de la ficha es completo
        titulo = limpiar(' '.join(response.css('h3:has(span.ornament)::text').getall()))
        if titulo:
            proyecto['titulo'] = titulo

        for item in response.css('ul.content_details li'):
            etiqueta = limpiar(item.css('span.text > span::text').get())
            if etiqueta in CAMPOS:
                valor = limpiar(' '.join(item.css('span.text::text').getall()))
                proyecto[CAMPOS[etiqueta]] = valor

        for bloque in response.css('div.content_info'):
            etiqueta = limpiar(bloque.css('div.content_title span.text::text').get())
            if etiqueta in RESUMENES:
                texto = '\n'.join(bloque.css('p ::text').getall())
                proyecto[RESUMENES[etiqueta]] = '\n'.join(
                    limpiar(linea) for linea in texto.splitlines() if limpiar(linea)
                )

        yield proyecto
