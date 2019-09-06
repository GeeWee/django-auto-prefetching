import logging

dap_logger = logging.getLogger("django-auto-prefetching")
dap_logger.addHandler(logging.StreamHandler())
dap_logger.setLevel(logging.DEBUG)