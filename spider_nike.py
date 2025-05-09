import scrapy
import json
import logging
from urllib.parse import urljoin, quote
from spider_nike.items import NikeProductItem


class NikeApiSpider(scrapy.Spider):
    """
    A flexible Nike spider that:
    1. Loads the catalog page and extracts initial product data via __NEXT_DATA__
    2. Walks the Nike API JSON feed, following pagination links
    3. Visits each product's detail page to gather extended attributes and availability
    """
    name = 'spider_nike'
    allowed_domains = ['nike.com', 'www.nike.com', 'api.nike.com']
    api_base = 'https://api.nike.com'
    marketplace = 'CZ'
    lang = 'cs'
    consumer_channel = 'd9a5bc42-4b9c-4976-858a-f159cf99c647'
    catalog_path = '/cz/w/obuv-y7ok'
    default_headers = {
        'Accept': 'application/json',
        'nike-api-caller-id': 'com.nike:commerce.idpdp.mobile',
    }

    def start_requests(self):
        # Step 1: Request the catalog landing page to retrieve the initial product feed data
        url = f"https://www.nike.com{self.catalog_path}"
        self.logger.info(f"[START] Requesting catalog page: {url}")
        yield scrapy.Request(
            url,
            callback=self.parse_start_page,
            headers={'Accept': 'text/html'},
        )

    def parse_start_page(self, response):
        # Parse the HTML for the embedded __NEXT_DATA__ JSON
        text = response.xpath('//script[@id="__NEXT_DATA__"]/text()').get()
        if not text:
            self.logger.error("Could not find __NEXT_DATA__ script tag")
            return
        js = json.loads(text)
        wall = js.get('props', {}).get('pageProps', {}).get('initialState', {}).get('Wall', {})

        # Enqueue detail page requests for each product in the initial catalog grouping
        for grouping in wall.get('productGroupings', []):
            for prod in grouping.get('products', []) or []:
                item = self.convert_product_dict_into_item(prod)
                style_color = prod.get('styleColor') or item['pid']
                if item.get('product_url'):
                    yield scrapy.Request(
                        item['product_url'],
                        callback=self.parse_product_page,
                        meta={'item': item, 'style_color': style_color},
                        headers=self.default_headers,
                    )
        # Follow the first pagination link from the catalog JSON
        next_endpoint = wall.get('pageData', {}).get('next')
        if next_endpoint:
            self.logger.info(f"[CATALOG] Next API endpoint: {next_endpoint}")
            yield self.create_api_request(next_endpoint)

    def create_api_request(self, endpoint: str):
        # Build a full URL for the Nike API endpoint, handling relative paths
        url = endpoint if endpoint.startswith('http') else urljoin(self.api_base, endpoint)
        return scrapy.Request(
            url,
            callback=self.parse_api_feed,
            headers=self.default_headers,
            dont_filter=True,
        )

    def parse_api_feed(self, response):
        """
        Step 2: Parse the Nike API JSON feed for product entries and pagination.
        Supports both grouped page-JSON and objects-JSON structures.
        """
        try:
            data = json.loads(response.text or '{}')
        except (json.JSONDecodeError, ValueError):
            self.logger.error("Failed to decode JSON from API feed", exc_info=True)
            return

        # If this response contains grouped product data
        if 'productGroupings' in data:
            self.logger.info(f"[API-GROUP] Processing grouped feed at {response.url}")
            for grouping in data.get('productGroupings', []):
                for prod in grouping.get('products', []) or []:
                    item = self.convert_product_dict_into_item(prod)
                    style_color = prod.get('styleColor') or item['pid']
                    if item.get('product_url'):
                        yield scrapy.Request(
                            item['product_url'],
                            callback=self.parse_product_page,
                            meta={'item': item, 'style_color': style_color},
                            headers=self.default_headers,
                        )
                    else:
                        yield item
            # Handle pagination links in the grouped JSON
            next_url = data.get('pages', {}).get('next') or data.get('pageData', {}).get('next')
            if next_url:
                self.logger.info(f"[API-GROUP] Next page: {next_url}")
                yield self.create_api_request(next_url)
            return

        # Otherwise, handle the flat objects-JSON variant
        if 'objects' in data:
            products = data['objects']
        elif 'data' in data and 'objects' in data['data']:
            products = data['data']['objects']
        else:
            products = data.get('data', {}).get('products', {}).get('products', [])

        self.logger.info(f"[API] Found {len(products)} products at {response.url}")
        for prod in products:
            item = self.convert_product_dict_into_item(prod)
            style_color = prod.get('styleColor') or item['pid']
            if item.get('product_url'):
                yield scrapy.Request(
                    item['product_url'],
                    callback=self.parse_product_page,
                    meta={'item': item, 'style_color': style_color},
                    headers=self.default_headers,
                )
            else:
                yield item

        # Follow pagination links in flat JSON
        paging = data.get('paging') or data.get('data', {}).get('paging')
        if paging:
            next_link = paging.get('next') or paging.get('nextAnchor')
            if next_link:
                self.logger.info(f"[API] Paginate next: {next_link}")
                yield self.create_api_request(next_link)

    def convert_product_dict_into_item(self, product: dict) -> NikeProductItem:
        # Map the JSON product dictionary into a NikeProductItem instance
        item = NikeProductItem()
        item['pid'] = product.get('productCode') or product.get('globalProductId') or product.get('internalPid')
        copy = product.get('copy', {})
        item['title'] = copy.get('title', '').replace('\xa0', ' ')
        subtitle = copy.get('subTitle')
        item['subtitle'] = subtitle.replace('\xa0', ' ') if subtitle else None
        item['description'] = product.get('description', '')
        prices = product.get('prices', {})
        item['current_price'] = prices.get('currentPrice')
        item['empl_price'] = prices.get('employeePrice')
        item['full_price'] = prices.get('initialPrice')
        item['currency'] = prices.get('currency')
        item['discount_percentage'] = prices.get('discountPercentage')
        display = product.get('displayColors', {})
        simple = display.get('simpleColor', {})
        item['color_description'] = display.get('colorDescription')
        item['color_label'] = simple.get('label')
        item['color_hex'] = simple.get('hex')
        item['featured_attributes'] = product.get('featuredAttributes')
        item['badge_attribute'] = product.get('badgeAttribute')
        item['badge_label'] = product.get('badgeLabel')
        item['product_type'] = product.get('productType')
        item['product_subtype'] = product.get('productSubType')
        raw_url = product.get('pdpUrl', {}).get('url')
        if raw_url:
            item['product_url'] = raw_url if raw_url.startswith('http') else urljoin(self.api_base, raw_url)
        return item

    def parse_product_page(self, response):
        # Step 3: Extract detailed product info and prepare availability request
        item = response.meta['item']
        style_color = response.meta['style_color']
        pid = item['pid']
        try:
            txt = response.xpath('//script[@id="__NEXT_DATA__"]/text()').get() or '{}'
            js = json.loads(txt)
            groups = js.get('props', {}).get('pageProps', {}).get('productGroups', [])
            selected = None
            for group in groups:
                products = group.get('products', {})
                if pid in products:
                    selected = products[pid]
                    break
            if not selected and groups:
                selected = next(iter(groups[0].get('products', {}).values()), None)
            if not selected:
                yield item
                return

            info = selected.get('productInfo', {})
            item['description'] = info.get('productDescription', '')
            item['enhanced_benefits'] = info.get('enhancedBenefits', [])
            item['features'] = info.get('featuresAndBenefits', [])
            item['details'] = info.get('productDetails', [])
            item['origins'] = info.get('origins', [])
            item['status_modifier'] = selected.get('statusModifier')
            item['badge'] = selected.get('badgeAttribute')
            item['badge_label'] = selected.get('badgeLabel')

            # Collect all images in high resolution
            images = []
            for img in selected.get('contentImages', []):
                props = img.get('properties', {})
                for key in ('portrait', 'squarish'):
                    url = props.get(key, {}).get('url')
                    if url:
                        images.append(url)
            item['all_images'] = [
                u.replace('/t_default/', '/t_PDP_1728_v1/f_auto,q_auto:eco/') if '/t_default/' in u else u
                for u in images
            ]

            # Prepare size availability lookup
            size_list = [
                {'label_EU': s.get('localizedLabel'), 'gtin': s.get('gtins', [{}])[0].get('gtin')}
                for s in selected.get('sizes', []) if s.get('localizedLabel')
            ]
            availability_url = (
                f"{self.api_base}/deliver/available_gtins/v3"
                f"?filter=styleColor({quote(style_color)})&filter=merchGroup(EU)"
            )
            yield scrapy.Request(
                availability_url,
                callback=self.parse_availability,
                headers=self.default_headers,
                meta={'item': item, 'raw_sizes': size_list},
                dont_filter=True,
            )
        except Exception:
            self.logger.error(f"Error parsing detail page for {pid}", exc_info=True)
            yield item

    def parse_availability(self, response):
        """
        Step 4: Parse availability JSON and attach size and stock data.
        """
        item = response.meta['item']
        raw_sizes = response.meta['raw_sizes']
        try:
            data = json.loads(response.text or '{}')
            objects = data.get('objects', [])
            availability_map = {o.get('gtin'): o for o in objects}
            sizes = []
            for sz in raw_sizes:
                label = sz.get('label_EU') or sz.get('label')
                obj = availability_map.get(sz.get('gtin'), {})
                sizes.append({
                    'label_EU': label,
                    'status': obj.get('level', 'OOS'),
                    'available': bool(obj.get('available', False)),
                })
            item['sizes'] = sizes
            item['in_stock'] = any(s['available'] for s in sizes)
        except Exception:
            self.logger.error(f"Error parsing availability for {item.get('pid')}", exc_info=True)
        yield item