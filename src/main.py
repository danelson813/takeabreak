import csv
import asyncio
from fake_useragent import UserAgent
from loguru import logger
from selectolax.lexbor import LexborHTMLParser
from playwright.async_api import async_playwright

ua = UserAgent()
url = "https://www.flowershopping.com/special-promotions/best-sellers?p=1"


def save_csv(list_, filename="results.csv"):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        keys = list_[0].keys()
        writer = csv.DictWriter(f, keys)
        writer.writeheader()
        writer.writerows(list_)


async def fetch(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent=ua.random,
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )

        page = await context.new_page()

        await page.goto(url, wait_until="domcontentloaded", timeout=90000)

        html = await page.content()
        logger.debug(html[:1000])
        await page.close()
        return html


def parse(html):
    tree = LexborHTMLParser(html)
    # The container for each product
    cards = tree.css("li.item.product-item")
    results = []

    for card in cards:
        name_node = card.css_first("strong.product-item-name a")

        # 1. Look for the Sale Price (Final Price)
        # Often inside a span with the class 'price-wrapper' or 'price-container'
        sale_price_node = card.css_first(".special-price .price") or card.css_first(
            "[data-price-type='finalPrice'] .price"
        )

        # 2. Look for the Original Price (Old Price)
        old_price_node = card.css_first(".old-price .price") or card.css_first(
            "[data-price-type='oldPrice'] .price"
        )

        # 3. Fallback: If it's not on sale, there's just one price
        if not sale_price_node:
            sale_price_node = card.css_first(".price-box .price")

        if name_node:
            results.append(
                {
                    "name": name_node.text(strip=True),
                    # We use .text(strip=True) to avoid whitespace and "Sale" labels
                    "sale_price": sale_price_node.text(strip=True)
                    if sale_price_node
                    else "N/A",
                    "original_price": old_price_node.text(strip=True)
                    if old_price_node
                    else "N/A",
                    "link": name_node.attributes.get("href"),
                }
            )

    return results


async def main(url):
    html = await fetch(url)
    cards = parse(html)
    return cards


if __name__ == "__main__":
    list_ = asyncio.run(main(url))
    if list_:
        print(f"Captured {len(list_)} items.")
        # print(list_[0])
        save_csv(list_)
    else:
        print("The list is empty. Check selectors.")
