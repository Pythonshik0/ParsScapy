import time
import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.http import Request
import datetime
import json


# Для запуска перейти в spiders и написать команду scrapy crawl second_spiders -O second.json
class SecondSpidersSpider(CrawlSpider):
    name = "second_spiders"
    allowed_domains = ["fix-price.com"]

    def __init__(self, *args, **kwargs):
        super(SecondSpidersSpider, self).__init__(*args, **kwargs)

        with open('category.json') as f:  # Загружаем JSON файл с категориями
            data = json.load(f)
            categories = data['main_category']  # Сохраняем список категорий из JSON

        self.start_urls = categories

    def parse_start_url(self, response, **kwargs):
        return self.parse_item(response)

    def parse_item(self, response):
        timestamp = int(datetime.datetime.now().timestamp()) #Время осздания записи
        hrefs = response.css('div.description a.title::attr(href)').getall() #url товаров
        headers = {
            'Set-Cookie:': '_cfuvid=1KLMCnDcCp85iQE97OA1QPqQC4R2i_jpznkj3LlYdAk-1711601092465-0.0.1.1-604800000; path=/; domain=.fix-price.com; HttpOnly; Secure; SameSite=None',
            'X-City': '55',
        }

        for href in hrefs:
            item = {
                "timestamp": timestamp,
                "RPC": "",
                "url": response.urljoin(href),
                "title": "title",
                "marketing_tags": "Динамическая загрузка через Java Script",
                "brand": "",
                "section": "",
                "price_data": {
                    "current": "Динамическая загрузка через Java Script", # str  # Цена со скидкой, если скидки нет то = original.
                    "original": "", # float # Оригинальная цена.
                    "sale_tag": "Динамическая загрузка через Java Script" # float # Если есть скидка на товар то необходимо вычислить процент скидки и записать формате: "Скидка {discount_percentage}%".
                },
                "stock": {
                    "in_stock": "Динамическая загрузка через Java Script -> при нажатии на кнопку",  # Есть товар в наличии в магазине или нет.
                    "count": "0",
                },
                "assets": {
                    "main_image": "str",  # Ссылка на основное изображение товара.
                    "set_images": ["str"],  # Список ссылок на все изображения товара.
                    "view360": "Изображений в формате 360 не было найдено",  # Список ссылок на изображения в формате 360.
                    "video": "Видео не было найдено в данных категориях"  # Список ссылок на видео/видеообложки товара.
                },
                "metadata": {
                    "__description": "", # Описание товара
                },
                "variants": "Для данных категорий не предусмотрен выбор товара из нескольких, данная функция открыта в корзине", # Кол-во вариантов у товара в карточке (За вариант считать только цвет или объем/масса. Размер у одежды или обуви варинтами не считаются).
            }

            url = response.urljoin(href)
            yield Request(url, callback=self.parse_linked_item, meta={'item': item}, headers=headers)

        next_page = response.css('a.next::attr(href)').get()
        if next_page:
            yield Request(response.urljoin(next_page), callback=self.parse_item)

    @staticmethod
    def parse_linked_item(response):
        item = response.meta['item']
        properties = response.css('div.properties p.property')

        # Получения описания товара и характеристик
        description = response.css('div.product-details')
        item['metadata']['__description'] = description.css('div.description::text').get()
        for prop in properties:
            KEY = prop.css('span.title::text').get()
            if KEY == 'Код товара':
                item['RPC'] = prop.css('span.value::text').get()
            if KEY != 'Бренд':
                value = prop.css('span.value::text').get()
                item["metadata"][KEY] = value
            else:
                item['brand'] = prop.css('span.value a.link::text').get()

        # Обработка title
        title = response.css('div.product-details')
        item['title'] = title.css('h1.title::text').get()

        # Обработка section
        section = response.css('.breadcrumbs .crumb')
        section_list = []
        for sec in section:
            name = sec.css('span.text::text').get()
            if name is not None:
                section_list.append(name)  # добавляем имя раздела в список
        item['section'] = section_list

        #Оригинальная цена | Загрузка статичная не через JS -> itemprop="price"
        original_price_text = response.css('div.price-quantity-block meta[itemprop="price"]::attr(content)').get()
        item['price_data']['original'] = original_price_text

        #Цена со скидкой | НЕ РАБОТАЕТ
        # baa = response.css('div.risk-information')
        price = response.css('div.special-price::text').extract_first()
        item['price_data']['sale_tag'] = price

        # Несколько ссылок на картинки товара
        img = []
        image_elements = response.css('div.swiper-slide img.thumbs-image')
        for element in image_elements:
            image_url = element.css('img::attr(src)').get()
            img.append(image_url)
        if len(img) < 1:
            item['assets']['set_images'] = 'На странице одно изображение'

        item['assets']['set_images'] = img

        #Если картинка одна или если картинок много
        image_url_main = response.css('link[itemprop="contentUrl"]::attr(href)').get()
        item['assets']['main_image'] = image_url_main

        # item['price_data']['current'] = original_price_text[0:]
        # if original_price_text:
        #     original_price_text = original_price_text.replace(' ₽', '').replace(',', '.')
        #     original_price = float(original_price_text)
        #     item['price_data']['current'] = original_price
        # else:
        #     item['price_data']['current'] = None

        # current = price_data.css('div.special-price::text').get()
        # if current == 'null':
        #     item['price_data']['current'] = price_data.css('div.regular-price::text').get()
        # else:
        #     item['price_data']['current'] = price_data.css('div.special-price::text').get()
        #     sale_tag = price_data.css('div.regular-price.old-price::text').get()
        #     sale_tag = str(sale_tag).replace(",", '.')
        #     # 100.0 * (X - Y) / Y
        #     if current is not None and sale_tag is not None:
        #         current = float(current.replace(',', '.'))
        #         sale_tag = float(sale_tag.replace(',', '.'))
        #         discount = 100.0 * (sale_tag - current) / sale_tag
        #         item['price_data']['sale_tag'] = f"Скидка {discount}%"
        #     else:
        #         item['price_data']['sale_tag'] = "Скидка не найдена"
        return item
