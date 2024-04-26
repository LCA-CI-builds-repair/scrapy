"""
This module contains the default values for all settings used by Scrapy.

For more information about these settings you can read the settings
documentation in docs/topics/settings.rst

Scrapy developers, if you add a setting here remember to:

* add it in alphabetical order
* group similar settings without leaving blank lines
* add its documentation to the available settings documentation
  (docs/topics/settings.rst)

"""

import sys
from importlib import import_module
from pathlib import Path

# Add missing imports for default settings used by Scrapy
# Add other necessary imports as needed

ADDONS = {}

AJAXCRAWL_ENABLED = False

ASYNCIO_EVENT_LOOP = None

AUTOTHROTTLE_ENABLED = False
AUTOTHROTTLE_DEBUG = False
AUTOTHROTTLE_MAX_DELAY = 60.0
AUTOTHROTTLE_START_DELAY = 5.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0

BOT_NAME = "scrapybot"

CLOSESPIDER_TIMEOUT = 0
CLOSESPIDER_PAGECOUNT = 0
CLOSESPIDER_ITEMCOUNT = 0
CLOSESPIDER_ERRORCOUNT = 0

COMMANDS_MODULE = ""

COMPRESSION_ENABLED = True

CONCURRENT_ITEMS = 100

CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 8
CONCURRENT_REQUESTS_PER_IP = 0

COOKIES_ENABLED = True
COOKIES_DEBUG = False

DEFAULT_ITEM_CLASS = "scrapy.item.Item"

DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en",
}

DEPTH_LIMIT = 0
DEPTH_STATS_VERBOSE = False
DEPTH_PRIORITY = 0

DNSCACHE_ENABLED = True
DNSCACHE_SIZE = 10000
DNS_RESOLVER = "scrapy.resolver.CachingThreadedResolver"
DNS_TIMEOUT = 60

DOWNLOAD_DELAY = 0

DOWNLOAD_HANDLERS = {}
DOWNLOAD_HANDLERS_BASE = {
    "data": "scrapy.core.downloader.handlers.datauri.DataURIDownloadHandler",
    "file": "scrapy.core.downloader.handlers.file.FileDownloadHandler",
    "http": "scrapy.core.downloader.handlers.http.HTTPDownloadHandler",
    "https": "scrapy.core.downloader.handlers.http.HTTPDownloadHandler",
    "s3": "scrapy.core.downloader.handlers.s3.S3DownloadHandler",
    "ftp": "scrapy.core.downloader.handlers.ftp.FTPDownloadHandler",
}

DOWNLOAD_TIMEOUT = 180  # 3mins

DOWNLOAD_MAXSIZE = 1024 * 1024 * 1024  # 1024m
DOWNLOAD_WARNSIZE = 32 * 1024 * 1024  # 32m

DOWNLOAD_FAIL_ON_DATALOSS = True

DOWNLOADER = "scrapy.core.downloader.Downloader"

DOWNLOADER_HTTPCLIENTFACTORY = (
    "scrapy.core.downloader.webclient.ScrapyHTTPClientFactory"
)
DOWNLOADER_CLIENTCONTEXTFACTORY = (
    "scrapy.core.downloader.contextfactory.ScrapyClientContextFactory"
)
DOWNLOADER_CLIENT_TLS_CIPHERS = "DEFAULT"
# Use highest TLS/SSL protocol version supported by the platform, also allowing negotiation:
DOWNLOADER_CLIENT_TLS_METHOD = "TLS"
DOWNLOADER_CLIENT_TLS_VERBOSE_LOGGING = False

DOWNLOADER_MIDDLEWARES = {}
    "scrapy.downloadermiddlewares.robotstxt.RobotsTxtMiddleware": 100,
    "scrapy.downloadermiddlewares.httpauth.HttpAuthMiddleware": 300,
    "scrapy.downloadermiddlewares.downloadtimeout.DownloadTimeoutMiddleware": 350,
    "scrapy.downloadermiddlewares.defaultheaders.DefaultHeadersMiddleware": 400,
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": 500,
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": 550,
    "scrapy.downloadermiddlewares.ajaxcrawl.AjaxCrawlMiddleware": 560,
    "scrapy.downloadermiddlewares.redirect.MetaRefreshMiddleware": 580,
    "scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware": 590,
    "scrapy.downloadermiddlewares.redirect.RedirectMiddleware": 600,
    "scrapy.downloadermiddlewares.cookies.CookiesMiddleware": 700,
    "scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware": 750,
    "scrapy.downloadermiddlewares.stats.DownloaderStats": 850,
    "scrapy.downloadermiddlewares.httpcache.HttpCacheMiddleware": 900,
    # Downloader side
}

DOWNLOADER_STATS = True

DUPEFILTER_CLASS = "scrapy.dupefilters.RFPDupeFilter"

# Add missing settings and comments as needed