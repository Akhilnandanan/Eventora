import re

from playwright.sync_api import expect


def test_visitor_can_open_home_page_and_browse_services(page):
    """A first end-to-end test: a visitor can reach Eventora's services page."""
    page.goto("http://127.0.0.1:8000/", wait_until="networkidle")

    expect(page).to_have_title(re.compile("Eventora"))
    expect(page.get_by_role("link", name="Eventora")).to_be_visible()
    page.get_by_role("link", name="Services", exact=True).click()
    expect(page).to_have_url(re.compile(r"/services/"))
