"""Download handlers for http and https schemes
"""
from scrapy.utils.misc import build_from_crawler, load_object
from scrapy.utils.python import to_unicode


class HTTP10DownloadHandler:
    lazy = False

    def __init__(self, settings, crawler=None):
        self.HTTPClientFactory = load_object(settings["DOWNLOADER_HTTPCLIENTFACTORY"])
        self.ClientContextFactory = load_object(
            settings["DOWNLOADER_CLIENTCONTEXTFACTORY"]
        )
        self._settings = settings
        self._crawler = crawler

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings, crawler)

    def download_request(self, request, spider):
        """Return a deferred for the HTTP download"""
        factory = self.HTTPClientFactory(request)
        self._connect(factory)
        return factory.deferred

    def _connect(self, factory):
        from twisted.internet import reactor

        host, port = to_unicode(factory.host), factory.port
        if factory.scheme == b"https":
            client_context_factory = build_from_crawler(
                objcls=self.ClientContextFactory,
                crawler=self._crawler,
                method=None, # Add method=None argument
            )
            return reactor.connectSSL(host, port, factory, client_context_factory)
        return reactor.connectTCP(host, port, factory)
