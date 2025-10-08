import scrapy


class CourseVideosSpider(scrapy.Spider):
    name = "course_videos"
    allowed_domains = ["go.van-gerrevink.eu"]
    start_urls = ["https://go.van-gerrevink.eu/"]

    def parse(self, response):
        pass
