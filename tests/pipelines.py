"""
So    def open_spider(self, spider):
        pass

    def process_item(self, item, spider):
        return item


class ProcessWithZeroDivisionErrorPipeline:
    def process_item(self, item, spider):
        passes used for testing
"""


class ZeroDivisionErrorPipeline:
    def open_spider(self, spider):
        1 / 0

    def process_item(self, item, spider):
        return item


class ProcessWithZeroDivisionErrorPipeline:
    def process_item(self, item, spider):
        1 / 0
