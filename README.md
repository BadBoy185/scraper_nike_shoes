# scraper\_nike\_shoes

A standalone Scrapy script (`nike_scraper.py`) for collecting detailed information about Nike sneakers from the CZ (Czech) catalog.

Since only the `nike_scraper.py` file is provided, you will need to set up the Python environment and dependencies before running the scraper

---

## 🚀 Quickstart

1. **Install Scrapy**
   Install Scrapy and other core dependencies via pip:

   ```bash
   pip install scrapy
   ```

   If you don’t have pip or virtualenv, see [https://docs.python.org/3/installing/#installing-packages](https://docs.python.org/3/installing/#installing-packages), and for full Scrapy documentation and tutorials visit [https://scrapy.org/](https://scrapy.org/).

2. **Download the Script**
   Place `nike_scraper.py` into your working directory (or clone the repo above).

3. **Run the Scraper**
   Use Scrapy’s `runspider` command

   ```bash
   scrapy runspider nike_scraper.py -o items.json
   ```

   This will execute the embedded spider in `nike_scraper.py` and output to `items.json`.

4. **Check Results**
   Inspect `items.json` to verify all products have been collected.

---

## 📦 Data Output Example

After completion, `items.json` will contain an array of JSON objects. Sample entry:

```json
{
  "pid": "AR3565-103",
  "title": "Nike Shox R4",
  "subtitle": "Dámské boty",
  "description": "Nike Shox R4, modern reinterpretation of the 2001 classic...",
  "current_price": 149.99,
  "empl_price": 149.99,
  "full_price": 149.99,
  "currency": "EUR",
  "discount_percentage": 0,
  "color_description": "Bílá/Phantom/Red/Bílá",
  "color_label": "Bílá",
  "color_hex": "EEF3FF",
  "product_url": "https://www.nike.com/cz/t/boty-shox-r4-wQWPrJH5/AR3565-103",
  "features": [...],
  "details": [...],
  "all_images": ["https://static.nike.com/...png", ...],
  "sizes": [
    {"label_EU": "35.5", "status": "HIGH", "available": true},
    {"label_EU": "36",   "status": "HIGH", "available": true}
  ],
  "in_stock": true
}
```

---

