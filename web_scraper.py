#Source Code
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import csv
import time
import argparse
from requests.adapters import HTTPAdapter, Retry
BASE_URL = "http://books.toscrape.com/"
RATING_MAP = {
    "One": 1,
    "Two": 2,
    "Three": 3,
    "Four": 4,
    "Five": 5
}
HEADERS = {
    "User-Agent": "CodeAlpha-Intern/1.0 (+https://github.com/yourusername)"
}
def create_session():
    s = requests.Session()
    retries = Retry(total=5, backoff_factor=0.5, status_forcelist=[500,502,503,504])
    s.mount("http://", HTTPAdapter(max_retries=retries))
    s.headers.update(HEADERS)
    return s
def parse_rating(tag):
    classes = tag.get("class", [])
    for c in classes:
        if c in RATING_MAP:
            return RATING_MAP[c]
    return None
def clean_price(price_str):
    return float(price_str.replace("£", "").strip())
def parse_book_page(session, book_url):
    """Fetch product page and extract UPC, category, description"""
    r = session.get(book_url, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    upc = ""
    table = soup.find("table", {"class": "table table-striped"})
    if table:
        rows = table.find_all("tr")
        for row in rows:
            th = row.find("th").get_text(strip=True)
            td = row.find("td").get_text(strip=True)
            if th == "UPC":
                upc = td
                break
    category = ""
    breadcrumb = soup.find("ul", {"class": "breadcrumb"})
    if breadcrumb:
        items = breadcrumb.find_all("li")
        if len(items) >= 3:
            category = items[2].get_text(strip=True)
    desc = ""
    desc_tag = soup.find("div", {"id": "product_description"})
    if desc_tag:
        p = desc_tag.find_next_sibling("p")
        if p:
            desc = p.get_text(strip=True)
    return upc, category, desc
def scrape_all_books(output_csv):
    session = create_session()
    page = 1
    all_books = []
    print("Starting scraping from:", BASE_URL)
    while True:
        page_url = urljoin(BASE_URL, f"catalogue/page-{page}.html")
        print(f"Fetching page {page} -> {page_url}")
        resp = session.get(page_url, timeout=10)
        if resp.status_code == 404:
            print("No more pages. Stopping.")
            break
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        articles = soup.find_all("article", {"class": "product_pod"})
        if not articles:
            print("No products on page. Stopping.")
            break
        for art in articles:
            h3 = art.find("h3")
            a = h3.find("a")
            title = a.get("title", "").strip()
            href = a.get("href")
            product_url = urljoin(page_url, href)
            price_tag = art.find("p", {"class": "price_color"})
            price = clean_price(price_tag.get_text()) if price_tag else None
            stock_tag = art.find("p", {"class": "instock availability"})
            stock = stock_tag.get_text(strip=True) if stock_tag else ""
            rating_tag = art.find("p", {"class": "star-rating"})
            rating = parse_rating(rating_tag) if rating_tag else None
            try:
                upc, category, description = parse_book_page(session, product_url)
            except Exception as e:
                print(f"Warning: failed to fetch product page {product_url}: {e}")
                upc, category, description = "", "", ""
            book = {
                "title": title,
                "price": price,
                "stock": stock,
                "rating": rating,
                "product_page_url": product_url,
                "upc": upc,
                "category": category,
                "description": description
            }
            all_books.append(book)
            time.sleep(0.5)
        page += 1
        time.sleep(1.0)
    fieldnames = ["title", "price", "stock", "rating", "product_page_url", "upc", "category", "description"]
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for b in all_books:
            writer.writerow(b)
    print(f"Scraping complete. {len(all_books)} books written to {output_csv}")
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape books.toscrape.com")
    parser.add_argument("--output", "-o", default="books.csv", help="CSV output filename")
    args = parser.parse_args()
    scrape_all_books(args.output)
