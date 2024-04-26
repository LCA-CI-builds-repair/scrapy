"""
Some pipelines used for testing
"""


class ZeroDivisionErrorPipeline:
    def open_spider(self, spider):
        try:
            # Add appropriate code here
        except ZeroDivisionError:
            # Handle the ZeroDivisionError gracefully
            pass

    def process_item(self, item, spider):
        return item

class ProcessWithZeroDivisionErrorPipeline:
    def process_item(self, item, spider):
        1 / 0
