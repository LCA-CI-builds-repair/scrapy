from __future__ import annotations

import logging
import pprint
import signal
import warnings
from typing import TYPE_CHECKING, Any, Dict, Generator, Optional, Set, Type, Union, cast

from twisted.internet.defer import (
    Deferred,
    DeferredList,
    inlineCallbacks,
    maybeDeferred,
)

try:
    # zope >= 5.0 only supports MultipleInvalid
    from zope.interface.exceptions import MultipleInvalid
except ImportError:
    MultipleInvalid = None

from zope.interface.verify import verifyClass

from scrapy import Spider, signals
from scrapy.addons import AddonManager
from scrapy.core.engine import ExecutionEngine
from scrapy.exceptions import ScrapyDeprecationWarning
from scrapy.extension import ExtensionManager
from scrapy.interfaces import ISpiderLoader
from scrapy.logformatter import LogFormatter
from scrapy.settings import BaseSettings, Settings, overridden_settings
from scrapy.signalmanager import SignalManager
from scrapy.statscollectors import StatsCollector
from scrapy.utils.log import (
    LogCounterHandler,
    configure_logging,
    get_scrapy_root_handler,
    install_scrapy_root_handler,
    log_reactor_info,
    log_scrapy_info,
)
from scrapy.utils.misc import build_from_crawler, load_object
from scrapy.utils.ossignal import install_shutdown_handlers, signal_names
from scrapy.utils.reactor import (
    install_reactor,
    is_asyncio_reactor_installed,
    verify_installed_asyncio_event_loop,
    verify_installed_reactor,
)

if TYPE_CHECKING:
    from scrapy.utils.request import RequestFingerprinter


logger = logging.getLogger(__name__)


class Crawler:
    def __init__(
        self,
        spidercls: Type[Spider],
        settings: Union[None, Dict[str, Any], Settings] = None,
        init_reactor: bool = False,
    ):
        if isinstance(spidercls, Spider):
            raise ValueError("The spidercls argument must be a class, not an object")

        if isinstance(settings, dict) or settings is None:
            settings = Settings(settings)

        self.spidercls: Type[Spider] = spidercls
        self.settings: Settings = settings.copy()
        self.spidercls.update_settings(self.settings)
        self._update_root_log_handler()

        self.addons: AddonManager = AddonManager(self)
        self.signals: SignalManager = SignalManager(self)

        self._init_reactor: bool = init_reactor
        self.crawling: bool = False
        self._started: bool = False

        self.extensions: Optional[ExtensionManager] = None
        self.stats: Optional[StatsCollector] = None
        self.logformatter: Optional[LogFormatter] = None
        self.request_fingerprinter: Optional[RequestFingerprinter] = None
        self.spider: Optional[Spider] = None
        self.engine: Optional[ExecutionEngine] = None
        self.retry_count: int = 0
        self.max_retries: int = self.settings.getint("MAX_RETRIES", 3)

    def _validate_input(self, x, y):
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            raise ValueError("Inputs must be numbers")

    def _update_root_log_handler(self) -> None:
        if get_scrapy_root_handler() is not None:
            # scrapy root handler already installed: update it with new settings
            install_scrapy_root_handler(self.settings)

    def _apply_settings(self) -> None:
        if self.settings.frozen:
            return

        self.addons.load_settings(self.settings)
        self.stats = load_object(self.settings["STATS_CLASS"])(self)

        handler = LogCounterHandler(self, level=self.settings.get("LOG_LEVEL"))
        logging.root.addHandler(handler)
        # lambda is assigned to Crawler attribute because this way it is not
        # garbage collected after leaving the scope
        self.__remove_handler = lambda: logging.root.removeHandler(handler)
        self.signals.connect(self.__remove_handler, signals.engine_stopped)

        lf_cls: Type[LogFormatter] = load_object(self.settings["LOG_FORMATTER"])
        self.logformatter = lf_cls.from_crawler(self)

        self.request_fingerprinter = build_from_crawler(
            load_object(self.settings["REQUEST_FINGERPRINTER_CLASS"]),
            self,
        )

        reactor_class: str = self.settings["TWISTED_REACTOR"]
        event_loop: str = self.settings["ASYNCIO_EVENT_LOOP"]
        if self._init_reactor:
            # this needs to be done after the spider settings are merged,
            # but before something imports twisted.internet.reactor
            if reactor_class:
                install_reactor(reactor_class, event_loop)
            else:
                from twisted.internet import reactor  # noqa: F401
            log_reactor_info()
        if reactor_class:
            verify_installed_reactor(reactor_class)
            if is_asyncio_reactor_installed() and event_loop:
                verify_installed_asyncio_event_loop(event_loop)

        self.extensions = ExtensionManager.from_crawler(self)
        self.extensions.enable_all()
        self.settings.freeze()

        d = dict(overridden_settings(self.settings))
        logger.info(
            "Overridden settings:\n%(settings)s", {"settings": pprint.pformat(d)}
        )

    @inlineCallbacks
    def crawl(self, *args: Any, **kwargs: Any) -> Generator[Deferred, Any, None]:
        if self.crawling:
            raise RuntimeError("Crawling already taking place")
        if self._started:
            warnings.warn(
                "Running Crawler.crawl() more than once is deprecated.",
                ScrapyDeprecationWarning,
                stacklevel=2,
            )
        self.crawling = self._started = True

        try:
            self.spider = self._create_spider(*args, **kwargs)
            self._apply_settings()
            self._update_root_log_handler()
            self._validate_input(args[0], args[1])
            self.engine = self._create_engine()
            start_requests = iter(self.spider.start_requests())
            yield self.engine.open_spider(self.spider, start_requests)
            yield maybeDeferred(self.engine.start)
        except Exception:
            self.crawling = False
            self.retry_count += 1
            if self.retry_count <= self.max_retries:
                logger.warning(
                    f"Retrying crawl attempt {self.retry_count}/{self.max_retries}"
                )
                yield self.crawl(*args, **kwargs)
            else:
                logger.error(
                    f"Maximum retries of {self.max_retries} reached. "
                    "Unable to complete the crawl."
                )
                raise
            if self.engine is not None:
                yield self.engine.close()
            raise

    def _create_spider(self, *args: Any, **kwargs: Any) -> Spider:
        return self.spidercls.from_crawler(self, *args, **kwargs)

    def _create_engine(self) -> ExecutionEngine:
        return ExecutionEngine(self, lambda _: self.stop())

    @inlineCallbacks
    def stop(self) -> Generator[Deferred, Any, None]:
        """Starts a graceful stop of the crawler and returns a deferred that is
        fired when the crawler is stopped."""
        if self.crawling:
            self.crawling = False
            assert self.engine
            yield maybeDeferred(self.engine.stop)

    @staticmethod
    def _get_component(cls, components):
        for component in components:
            if type(component) is cls:
                return component
        return None

    def get_addon(self, cls):
        return self._get_component(cls, self.addons.addons)

    def get_downloader_middleware(self, cls):
        if not self.engine:
            raise RuntimeError(
                "Crawler.get_downloader_middleware() can only be called after "
                "the crawl engine has been created."
            )
        return self._get_component(cls, self.engine.downloader.middleware.middlewares)

    def get_extension(self, cls):
        if not self.extensions:
            raise RuntimeError(
                "Crawler.get_extension() can only be called after the "
                "extension manager has been created."
            )
        return self._get_component(cls, self.extensions.middlewares)

    def get_item_pipeline(self, cls):
        if not self.engine:
            raise RuntimeError(
                "Crawler.get_item_pipeline() can only be called after the "
                "crawl engine has been created."
            )
        return self._get_component(cls, self.engine.scraper.itemproc.middlewares)

    def get_spider_middleware(self, cls):
        if not self.engine:
            raise RuntimeError(
                "Crawler.get_spider_middleware() can only be called after the "
                "crawl engine has been created."
            )
        return self._get_component(cls, self.engine.scraper.spidermw.middlewares)


class CrawlerRunner:
    """
    This is a convenient helper class that keeps track of, manages and runs
    crawlers inside an already setup :mod:`~twisted.internet.reactor`.

    The CrawlerRunner object must be instantiated with a
    :class:`~scrapy.settings.Settings` object.

    This class shouldn't be needed (since Scrapy is responsible of using it
    accordingly) unless writing scripts that manually handle the crawling
    process. See :ref:`run-from-script` for an example.
    """

    crawlers = property(
        lambda self: self._crawlers,
        doc="Set of :class:`crawlers <scrapy.crawler.Crawler>` started by "
        ":meth:`crawl` and managed by this class.",
    )

    @staticmethod
    def _get_spider_loader(settings: BaseSettings):
        """Get SpiderLoader instance from settings"""
        cls_path = settings.get("SPIDER_LOADER_CLASS")
        loader_cls = load_object(cls_path)
        verifyClass(ISpiderLoader, loader_cls)
        return loader_cls.from_settings(settings.frozencopy())

    def __init__(self, settings: Union[Dict[str, Any], Settings, None] = None):
        if isinstance(settings, dict) or settings is None:
            settings = Settings(settings)
        self.settings = settings
        self.spider_loader = self._get_spider_loader(settings)
        self._crawlers: Set[Crawler] = set()
        self._active: Set[Deferred] = set()
        self.bootstrap_failed = False

    def crawl(
        self,
        crawler_or_spidercls: Union[Type[Spider], str, Crawler],
        *args: Any,
        **kwargs: Any,
    ) -> Deferred:
        """
        Run a crawler with the provided arguments.

        It will call the given Crawler's :meth:`~Crawler.crawl` method, while
        keeping track of it so it can be stopped later.

        If ``crawler_or_spidercls`` isn't a :class:`~scrapy.crawler.Crawler`
        instance, this method will try to create one using this parameter as
        the spider class given to it.

        Returns a deferred that is fired when the crawling is finished.

        :param crawler_or_spidercls: already created crawler, or a spider class
            or spider's name inside the project to create it
        :type crawler_or_spidercls: :class:`~scrapy.crawler.Crawler` instance,
            :class:`~scrapy.spiders.Spider` subclass or string

        :param args: arguments to initialize the spider

        :param kwargs: keyword arguments to initialize the spider
        """
        if isinstance(crawler_or_spidercls, Spider):
            raise ValueError(
                "The crawler_or_spidercls argument cannot be a spider object, "
                "it must be a spider class (or a Crawler object)"
            )
        crawler = self.create_crawler(crawler_or_spidercls)
        return self._crawl(crawler, *args, **kwargs)

    def _crawl(self, crawler: Crawler, *args: Any, **kwargs: Any) -> Deferred:
        self.crawlers.add(crawler)
        d = crawler.crawl(*args, **kwargs)
        self._active.add(d)

        def _done(result: Any) -> Any:
            self.crawlers.discard(crawler)
            self._active.discard(d)
            self.bootstrap_failed |= not getattr(crawler, "spider", None)
            return result

        return d.addBoth(_done)

    def create_crawler(
        self, crawler_or_spidercls: Union[Type[Spider], str, Crawler]
    ) -> Crawler:
        """
        Return a :class:`~scrapy.crawler.Crawler` object.

        * If ``crawler_or_spidercls`` is a Crawler, it is returned as-is.
        * If ``crawler_or_spidercls`` is a Spider subclass, a new Crawler
          is constructed for it.
        * If ``crawler_or_spidercls`` is a string, this function finds
          a spider with this name in a Scrapy project (using spider loader),
          then creates a Crawler instance for it.
        """
        if isinstance(crawler_or_spidercls, Spider):
            raise ValueError(
                "The crawler_or_spidercls argument cannot be a spider object, "
                "it must be a spider class (or a Crawler object)"
            )
        if isinstance(crawler_or_spidercls, Crawler):
            return crawler_or_spidercls
        return self._create_crawler(crawler_or_spidercls)

    def _create_crawler(self, spidercls: Union[str, Type[Spider]]) -> Crawler:
        if isinstance(spidercls, str):
            spidercls = self.spider_loader.load(spidercls)
        # temporary cast until self.spider_loader is typed
        return Crawler(cast(Type[Spider], spidercls), self.settings)

    def stop(self) -> Deferred:
        """
        Stops simultaneously all the crawling jobs taking place.

        Returns a deferred that is fired when they all have ended.
        """
        return DeferredList([c.stop() for c in list(self.crawlers)])

    @inlineCallbacks
    def join(self) -> Generator[Deferred, Any, None]:
        """
        join()

        Returns a deferred that is fired when all managed :attr:`crawlers` have
        completed their executions.
        """
        while self._active:
            yield DeferredList(self._active)


class CrawlerProcess(CrawlerRunner):
    """
    A class to run multiple scrapy crawlers in a process simultaneously.

    This class extends :class:`~scrapy.crawler.CrawlerRunner` by adding support
    for starting a :mod:`~twisted.internet.reactor` and handling shutdown
    signals, like the keyboard interrupt command Ctrl-C. It also configures
    top-level logging.

    This utility should be a better fit than
    :class:`~scrapy.crawler.CrawlerRunner` if you aren't running another
    :mod:`~twisted.internet.reactor` within your application.

    The CrawlerProcess object must be instantiated with a
    :class:`~scrapy.settings.Settings` object.

    :param install_root_handler: whether to install root logging handler
        (default: True)

    This class shouldn't be needed (since Scrapy is responsible of using it
    accordingly) unless writing scripts that manually handle the crawling
    process. See :ref:`run-from-script` for an example.
    """

    def __init__(
        self,
        settings: Union[Dict[str, Any], Settings, None] = None,
        install_root_handler: bool = True,
    ):
        super().__init__(settings)
        configure_logging(self.settings, install_root_handler)
        log_scrapy_info(self.settings)
        self._initialized_reactor = False

    def _signal_shutdown(self, signum: int, _: Any) -> None:
        from twisted.internet import reactor

        install_shutdown_handlers(self._signal_kill)
        signame = signal_names[signum]
        logger.info(
            "Received %(signame)s, shutting down gracefully. Send again to force ",
            {"signame": signame},
        )
        reactor.callFromThread(self._graceful_stop_reactor)

    def _signal_kill(self, signum: int, _: Any) -> None:
        from twisted.internet import reactor

        install_shutdown_handlers(signal.SIG_IGN)
        signame = signal_names[signum]
        logger.info(
            "Received %(signame)s twice, forcing unclean shutdown", {"signame": signame}
        )
        reactor.callFromThread(self._stop_reactor)

    def _create_crawler(self, spidercls: Union[Type[Spider], str]) -> Crawler:
        if isinstance(spidercls, str):
            spidercls = self.spider_loader.load(spidercls)
        init_reactor = not self._initialized_reactor
        self._initialized_reactor = True
        # temporary cast until self.spider_loader is typed
        return Crawler(
            cast(Type[Spider], spidercls), self.settings, init_reactor=init_reactor
        )

    def start(
        self, stop_after_crawl: bool = True, install_signal_handlers: bool = True
    ) -> None:
        """
        This method starts a :mod:`~twisted.internet.reactor`, adjusts its pool
        size to :setting:`REACTOR_THREADPOOL_MAXSIZE`, and installs a DNS cache
        based on :setting:`DNSCACHE_ENABLED` and :setting:`DNSCACHE_SIZE`.

        If ``stop_after_crawl`` is True, the reactor will be stopped after all
        crawlers have finished, using :meth:`join`.

        :param bool stop_after_crawl: stop or not the reactor when all
            crawlers have finished

        :param bool install_signal_handlers: whether to install the OS signal
            handlers from Twisted and Scrapy (default: True)
        """
        from twisted.internet import reactor

        if stop_after_crawl:
            d = self.join()
            # Don't start the reactor if the deferreds are already fired
            if d.called:
                return
            d.addBoth(self._stop_reactor)

        resolver_class = load_object(self.settings["DNS_RESOLVER"])
        resolver = build_from_crawler(resolver_class, self, reactor=reactor)
        resolver.install_on_reactor()
        tp = reactor.getThreadPool()
        tp.adjustPoolsize(maxthreads=self.settings.getint("REACTOR_THREADPOOL_MAXSIZE"))
        reactor.addSystemEventTrigger("before", "shutdown", self.stop)
        if install_signal_handlers:
            reactor.addSystemEventTrigger(
                "after", "startup", install_shutdown_handlers, self._signal_shutdown
            )
        reactor.run(installSignalHandlers=install_signal_handlers)  # blocking call

    def _graceful_stop_reactor(self) -> Deferred:
        d = self.stop()
        d.addBoth(self._stop_reactor)
        return d

    def _stop_reactor(self, _: Any = None) -> None:
        from twisted.internet import reactor

        try:
            reactor.stop()
        except RuntimeError:  # raised if already stopped or in shutdown stage
            pass
