import time
import random
import os
import requests
from threading import Thread
from playwright.sync_api import sync_playwright
from datetime import datetime

# Load webhooks from GitHub Secrets
WEBHOOK = os.environ["WEBHOOK"]           # main restock notifications
LOG_WEBHOOK = os.environ.get("LOG_WEBHOOK")  # optional live log channel

# Products to monitor
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

# ------------------------
# Discord helper functions
# ------------------------
def send(msg):
    """Send restock alert"""
    try:
        requests.post(WEBHOOK, json={"content": msg}, timeout=10)
    except:
        print("Restock webhook fail")

def log(msg):
    """Send console/log messages to Discord log channel and print locally"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"[{ts}] {msg}"
    print(full_msg)
    if LOG_WEBHOOK:
        try:
            requests.post(LOG_WEBHOOK, json={"content": full_msg}, timeout=10)
        except:
            print("Log webhook fail")

# ------------------------
# Notify bot active
# ------------------------
log(f"🚀 JD Sniper is now ACTIVE! Monitoring {len(PRODUCTS)} products.")

# ------------------------
# Helper to detect sizes
# ------------------------
def get_sizes(page):
    sizes = ["M"]
    buttons = page.locator("button")
    for i in range(buttons.count()):
        txt = buttons.nth(i).inner_text().strip()
        # simple heuristic: size usually short, contains number/letter
        if len(txt) <= 4 and any(c.isdigit() or c.isalpha() for c in txt):
            sizes.append(txt)
    return list(set(sizes))

# ------------------------
# Sniper function per product
# ------------------------
def sniper(browser, product):
    url = product["url"]
    name = product["name"]

    context = browser.new_context()
    page = context.new_page()

    log(f"🚀 Sniping {name}")

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
                        # click size
                        btn.click()
                        page.wait_for_timeout(600)
                        # click add to bag
                        add = page.locator("button:has-text('Add to Bag')")
                        add.click(timeout=4000)
                        # wait for confirmation
                        page.wait_for_selector("text=Added to Bag", timeout=4000)

                        if key not in seen:
                            send(f"🔥 JD RESTOCK\n{name}\nSize {size}\n{url}")
                            log(f"COPPABLE: {name} Size {size}")
                            seen.add(key)

                        # remove item from cart
                        page.goto("https://www.jdsports.co.uk/cart/")
                        page.wait_for_timeout(2000)
                        rem = page.locator("button:has-text('Remove')")
                        if rem.count() > 0:
                            rem.first.click()
                        page.wait_for_timeout(1500)
                    else:
                        if key in seen:
                            seen.remove(key)
                except Exception as e:
                    log(f"Error checking size {size} for {name}: {e}")

            # random delay between refreshes
            time.sleep(18 + random.randint(0, 6))

        except Exception as e:
            log(f"Error loading product {name}: {e}")
            time.sleep(10)

# ------------------------
# Main execution
# ------------------------
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    threads = []
    for product in PRODUCTS:
        t = Thread(target=sniper, args=(browser, product))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
