import re

from playwright.sync_api import expect


def test_customer_can_reach_booking_form(page):
    """A customer can open an active service and reach its booking form."""
    page.goto("http://127.0.0.1:8000/login/", wait_until="networkidle")
    page.locator('input[name="username"]').fill("demo_customer1")
    page.locator('input[name="password"]').fill("demo1234")
    page.get_by_role("button", name="Login").click()

    page.goto("http://127.0.0.1:8000/services/", wait_until="networkidle")
    page.get_by_role("link", name="View Details").first.click()
    page.get_by_role("link", name="Book Now").click()

    expect(page).to_have_url(re.compile(r"/services/\d+/book/"))
    expect(page.get_by_role("heading", name=re.compile(r"Book:"))).to_be_visible()
    expect(page.get_by_role("button", name="Send Booking Request")).to_be_visible()
