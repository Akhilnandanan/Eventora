from playwright.sync_api import expect


def test_customer_can_log_in(page):
    """A demo customer can log in through the normal Eventora login form."""
    page.goto("http://127.0.0.1:8000/login/", wait_until="networkidle")

    page.locator('input[name="username"]').fill("demo_customer1")
    page.locator('input[name="password"]').fill("demo1234")
    page.get_by_role("button", name="Login").click()

    expect(page).to_have_url("http://127.0.0.1:8000/")
    expect(page.get_by_text("Welcome back, demo_customer1!")).to_be_visible()
    page.get_by_role("button", name="Hi, Aditi").click()
    expect(page.get_by_role("link", name="Dashboard", exact=True)).to_be_visible()
