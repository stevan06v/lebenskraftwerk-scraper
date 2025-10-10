from urllib.parse import urlparse, parse_qs

import scrapy
from scrapy import FormRequest, Request
from playwright.async_api import TimeoutError as PlaywrightTimeoutError


def clean_vimeo_url(raw_src: str) -> str:
    if raw_src is None:
        return None
    src = raw_src.strip()
    if src.startswith("//"):
        src = "https:" + src
    parsed = urlparse(src)
    clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    return clean


class CourseVideosSpider(scrapy.Spider):
    name = "course_videos"
    login_page = 'https://go.van-gerrevink.eu/membership-access1709819901361?page_id=61563115&page_key=asyzbbxc13x64urd'

    async def start(self):
        yield scrapy.Request(
            self.login_page,
            callback=self.parse_login_page,
            meta={"playwright": True}
        )

    def parse_login_page(self, response):
        parsed = urlparse(response.url)
        q = parse_qs(parsed.query)
        page_id = q.get("page_id", [None])[0]
        page_key = q.get("page_key", [None])[0]

        self.logger.info(f"\n========================\n")
        self.logger.info(f"PAGE_ID: {page_id}")
        self.logger.info(f"PAGE_KEY: {page_key}")
        self.logger.info(f"\n========================\n")

        return scrapy.FormRequest(
                url="https://go.van-gerrevink.eu/members/sign_in",
                method="POST",
                formdata={
                    "member[email]": "jonathan@hochmeir.com",
                    "member[password]": "Test1234",
                    "member[page_key]": page_key or "asyzbbxc13x64urd",
                    "member[page_id]": page_id or "61563115",
                },
                callback=self.parse_list,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page": response.meta.get("playwright_page"),
                }
            )

    async def parse_list(self, response):
        page = response.meta["playwright_page"]

        # get all header elements
        headers = await page.query_selector_all("li.membershipNavTitle")

        for index, header in enumerate(headers):
            # get the title div
            div_title = await header.query_selector("div.title")
            class_name = await div_title.get_attribute("class")

            header_text_el = await div_title.query_selector("strong")
            if not header_text_el:
                header_text_el = await div_title.query_selector("span")

            header_text = await header_text_el.inner_text() if header_text_el else f"Header #{index}"

            section = await header.query_selector("xpath=following-sibling::li[contains(@class, 'membershipNavInner')]")
            if not section:
                print(f"No section found for header #{index}: {header_text}")
                continue

            section_class = await section.get_attribute("class")
            section_expanded = "in" in section_class

            if not section_expanded:
                await div_title.click()
                print(f"Expanded header: {header_text}")
                await page.wait_for_selector("li.membershipNavInner.in", timeout=2000)
            else:
                print(f"Already expanded: {header_text}")

            # scrape lessons from this section
            links = await section.query_selector_all("div > ul > li > a")

            for link in links:
                lesson_id = await link.get_attribute("data-lesson-id")
                lesson_name_el = await link.query_selector('span[data-cf-lesson-name="true"]')
                lesson_name = await lesson_name_el.inner_text() if lesson_name_el else None

                self.logger.info(f"Found lesson: {lesson_name} ({lesson_id})")

                await link.click()
                try:
                    await page.wait_for_selector("iframe[src*='vimeo.com']", timeout=2000)
                except PlaywrightTimeoutError:
                    self.logger.info(f"No video in lesson {lesson_id}, skipping")
                    continue

                iframe = await page.query_selector("iframe[src*='vimeo.com']")
                video_src = await iframe.get_attribute("src") if iframe else None

                title_el = await page.query_selector("div.ne.elHeadline")
                title_text = await title_el.inner_text() if title_el else None

                yield {
                    "module_title": header_text,
                    "lesson_id": lesson_id,
                    "lesson_name": lesson_name.strip() if lesson_name else None,
                    "video_url": clean_vimeo_url(video_src),
                    "video_title": title_text.strip() if title_text else None,
                }
