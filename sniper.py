import time
import random
import requests
from threading import Thread
from playwright.sync_api import sync_playwright
import os
WEBHOOK = os.environ["WEHBOOK"]

PRODUCTS = [
    {
        "url": "https://www.jdsports.co.uk/product/blue-technicals-quartz-tracksuit/19705743/",
        "name": "Technicals Tracksuit"
    },
    {
        "url": "https://www.jdsports.co.uk/product/blue-technicals-quartz-tracksuit/19714017/",
        "name": "North Face Hoodie"
    }
]

seen = set()

def send(msg):
    try:
        requests.post(WEBHOOK, json={"content": msg}, timeout=10)
    except:
        print("Webhook fail")

def get_sizes(page):
    sizes = ["M"]

    buttons = page.locator("button")

    for i in range(buttons.count()):

        txt = buttons.nth(i).inner_text().strip()

        if len(txt) <= 4 and any(c.isdigit() for c in txt):
            sizes.append(txt)

    return list(set(sizes))


def sniper(browser, product):

    url = product["url"]
    name = product["name"]

    context = browser.new_context()
    page = context.new_page()

    print(f"🚀 Sniping {name}")

    while True:

        try:

            page.goto(url, timeout=60000)
            page.wait_for_timeout(3500)

            sizes = get_sizes(page)

            for size in sizes:

                key = f"{url}_{size}"

                try:

                    btn = page.locator("button", has_text=size).first

                    if btn.is_visible() and btn.is_enabled():

                        btn.click()
                        page.wait_for_timeout(600)

                        add = page.locator("button:has-text('Add to Bag')")
                        add.click(timeout=4000)

                        page.wait_for_selector("text=Added to Bag", timeout=4000)

                        if key not in seen:

                            send(
                                f"🔥 JD RESTOCK\n"
                                f"{name}\n"
                                f"Size {size}\n"
                                f"{url}"
                            )

                            print("COPPABLE:", name, size)
                            seen.add(key)

                        # remove item
                        page.goto("https://www.jdsports.co.uk/cart/")
                        page.wait_for_timeout(2000)

                        rem = page.locator("button:has-text('Remove')")
                        if rem.count() > 0:
                            rem.first.click()

                        page.wait_for_timeout(1500)

                    else:
                        if key in seen:
                            seen.remove(key)

                except:
                    pass

            time.sleep(18 + random.randint(0,6))

        except Exception as e:
            print("Error:", name, e)
            time.sleep(10)


with sync_playwright() as p:

    browser = p.chromium.launch(headless=True)

    threads = []

    for product in PRODUCTS:

        t = Thread(target=sniper, args=(browser, product))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()
