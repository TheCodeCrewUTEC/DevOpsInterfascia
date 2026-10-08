import io
import re
import pdfplumber
import scrapy

# Encabezados de sección del CV (texto sacado del PDF de CVUy)
FIN_FORMACION = re.compile(r'^(Formación complementaria|Idiomas|Areas de actuación|Actuación profesional)$')
INICIO_PROYECTOS = re.compile(r'^PROYECTOS DE ')
FIN_PROYECTOS = re.compile(r'^(DOCENCIA|EXTENSIÓN|GESTIÓN ACADÉMICA|VÍNCULOS CON LA INSTITUCIÓN|ACTIVIDADES|'
                           r'LÍNEAS DE INVESTIGACIÓN|SERVICIO TÉCNICO ESPECIALIZADO|CARGA HORARIA|'
                           r'OTRAS ACTIVIDADES.*|SECTOR .*|Producción .*|Evaluaciones|Formación de RRHH)$')

FIN_LECTURA = re.compile(r'^(ARTÍCULOS PUBLICADOS|Producción científica)', re.M)

NIVELES = re.compile(r'^(POSDOCTORADO|DOCTORADO|MAESTRÍA|ESPECIALIZACIÓN/PERFECCIONAMIENTO|GRADO|PREGRADO|TÉCNICO)$')
ESTADOS = re.compile(r'^(CONCLUIDA|EN MARCHA|INCONCLUSA|ABANDONADA)$')
FECHAS = re.compile(r'\((\d{2}/)?\d{4}\s*-\s*(a la fecha|(\d{2}/)?\d{4})\s*\)$')


X_CONTENIDO = 165


class  CvuySpyder(scrapy.Spider):
    name = 'Investigador'
    start_urls = ['https://sni.org.uy/buscador/']

    custom_settings = {
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'AUTOTHROTTLE_ENABLED': True,
        'DOWNLOAD_TIMEOUT': 120,
        'FEED_EXPORT_ENCODING': 'utf-8',
    }

    def __init__(self, limit=0, solo_listado=0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.limit = int(limit)                      
        self.solo_listado = bool(int(solo_listado))  

    # listado de investigadores del SNI
    def parse(self, response):
        filas = [fila for fila in response.css('tr') if len(fila.css('td')) >= 6]
        if self.limit:
            filas = filas[:self.limit]

        for Investigador in filas:
            celdas = Investigador.css('td')
            investigador = {
                'nombre_completo': celdas[0].css('::text').get(default='').strip(),
                'nivel': celdas[1].css('::text').get(default='').strip(),
                'categoria': celdas[2].css('::text').get(default='').strip(),
                'area': celdas[3].css('::text').get(default='').strip(),
                'subarea': celdas[4].css('::text').get(default='').strip(),
                'link': response.urljoin(
                    Investigador.css('a.ver::attr(href)').get()
                ),
            }
            if self.solo_listado:
                yield investigador
                continue

            yield scrapy.Request(
                investigador['link'],
                callback=self.parse_cv,
                cb_kwargs={'investigador': investigador}
            )

    #CV de cada investigador
    def parse_cv(self, response, investigador):
        
        apellido, _, nombre = investigador['nombre_completo'].partition(',')

        lineas = self.lineas_pdf(response.body)
        yield {
            'nombre': nombre.strip(),
            'apellido': apellido.strip(),
            'institucion': self.institucion(lineas),
            'formacion': self.formacion(lineas),
            'proyectos': self.proyectos(lineas),
            **investigador,
        }

    def lineas_pdf(self, contenido):
       
        lineas = []
        with pdfplumber.open(io.BytesIO(contenido)) as pdf:
            for pagina in pdf.pages:
                pagina = pagina.crop((X_CONTENIDO, 0, pagina.width, pagina.height))
                texto = []
                for linea in pagina.extract_text_lines():
                    negrita = 'Bold' in linea['chars'][0]['fontname']
                    lineas.append((linea['text'].strip(), negrita))
                    texto.append(linea['text'])
                if FIN_LECTURA.search('\n'.join(texto)):
                    break
        return lineas

    def institucion(self, lineas):
        
        for i, (linea, negrita) in enumerate(lineas):
            if negrita and linea == 'INSTITUCIÓN PRINCIPAL':
                partes = []
                for siguiente, en_negrita in lineas[i + 1:]:
                    if en_negrita:
                        break
                    partes.append(siguiente)
                return ' '.join(partes)
        return ''

    def formacion(self, lineas):
        
        titulos = []
        nivel = estado = ''
        titulo = []
        dentro = False
        for i, (linea, negrita) in enumerate(lineas):
            if linea == 'Formación académica':
                dentro = True
                continue
            if not dentro:
                continue
            if FIN_FORMACION.match(linea):
                break

            if ESTADOS.match(linea):
                estado = linea
            elif NIVELES.match(linea):
                nivel = linea
            elif negrita:
                titulo.append(linea)  
                if FECHAS.search(linea):
                    titulos.append({
                        'nivel': nivel,
                        'estado': estado,
                        'titulo': ' '.join(titulo),
                        'institucion': lineas[i + 1][0] if i + 1 < len(lineas) else '',
                    })
                    titulo = []
            else:
                titulo = []
        return titulos

    def proyectos(self, lineas):
        
        proyectos = []
        titulo = []
        dentro = False
        for linea, negrita in lineas:
            if negrita and INICIO_PROYECTOS.match(linea):
                dentro, titulo = True, []
                continue
            if not dentro:
                continue
            if negrita and FIN_PROYECTOS.match(linea):
                dentro = False
                continue

            if negrita:
                titulo.append(linea)
                if FECHAS.search(linea):
                    completo = ' '.join(titulo)
                    if completo not in proyectos:
                        proyectos.append(completo)
                    titulo = []
            else:
                titulo = []
        return proyectos
