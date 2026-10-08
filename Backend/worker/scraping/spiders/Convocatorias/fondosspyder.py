import scrapy

class  FondosSpyder(scrapy.Spider):
    name = 'FondoInversor'
    start_urls = ['https://www.ande.org.uy/convocatorias/advanced-search/1938.html'] # ['https://www.ande.org.uy/convocatorias/advanced-search/1923.html']

    def parse(self, response):
        for Fondos in response.css('figure.uk-overlay'):
            yield {
                'nombre': Fondos.css('div.uk-margin.name::text').get(),
                'estado': Fondos.css('div.uk-margin.estado::text').get(),
                'link': response.urljoin(
                    Fondos.css('a.uk-position-cover::attr(href)').get()
                ),
            }

        siguiente = response.css(
                'a.next::attr(href)'
            ).get()

        if siguiente:
            yield response.follow(
                siguiente,
                callback=self.parse
            )