from playwright.sync_api import sync_playwright

URL = "https://dashboard-kpis-mantenimiento-asrs-ep8nttdf9imwcwvdnhhzpx.streamlit.app/"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        print(f"Visitando {URL} ...")
        page.goto(URL, wait_until="networkidle", timeout=60000)

        wake = page.locator("button:has-text('get this app back up')")
        if wake.count() > 0:
            print("Estaba dormida. Despertando...")
            wake.first.click()
            page.wait_for_timeout(30000)
            print("Despertada.")
        else:
            print("Ya estaba despierta.")
        browser.close()

if __name__ == "__main__":
    main()
