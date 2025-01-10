import warnings
from itertools import product
from unittest import TestCase

from scrapy.downloadermiddlewares.stats import DownloaderStats
from scrapy.exceptions import ScrapyDeprecationWarning
from scrapy.http import Request, Response
from scrapy.spiders import Spider
from scrapy.utils.test import get_crawler
from scrapy.utils.python import to_bytes

class MyException(Exception):
    pass


class TestDownloaderStats(TestCase):
    def setUp(self):
        self.crawler = get_crawler(Spider)
        self.spider = self.crawler._create_spider("scrapytest.org")
        self.mw = DownloaderStats(self.crawler.stats)

        self.crawler.stats.open_spider(self.spider)

        self.req = Request("http://scrapytest.org")
        self.res = Response("http://scrapytest.org", status=400)

    def assertStatsEqual(self, key, value):
        self.assertEqual(
            self.crawler.stats.get_value(key, spider=self.spider),
            value,
            f"Stats: {self.crawler.stats.get_stats(self.spider)}"
        )

    def test_process_request(self):
        self.mw.process_request(self.req, self.spider)
        self.assertStatsEqual("downloader/request_count", 1)

    def test_process_response(self):
        self.mw.process_response(self.req, self.res, self.spider)
        self.assertStatsEqual("downloader/response_count", 1)

    def test_response_len(self):
        # Test with different response body and header sizes
        for body, headers in [
            (b"", {}),
            (b"not_empty", {}),
            (b"", {"lang": "en"}),
            (b"", {"lang": "en", "User-Agent": "scrapy"}),
        ]:
            test_response = Response(url="http://scrapytest.org", status=200, body=body, headers=headers)
            self.crawler.stats.set_value("downloader/response_bytes", 0)
            self.mw.process_response(self.req, test_response, self.spider)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", ScrapyDeprecationWarning)
                resp_size = to_bytes(test_response)
            self.assertStatsEqual("downloader/response_bytes", resp_size)

    def test_process_exception(self):
        self.mw.process_exception(self.req, MyException(), self.spider)
        self.assertStatsEqual("downloader/exception_count", 1)
        self.assertStatsEqual(
            "downloader/exception_type_count/MyException",
            1,
        )

    def tearDown(self):
        self.crawler.stats.close_spider(self.spider, "")
