import sys
from pathlib import Path

# CRONE-based задача, можна повішати на ніч, оскільки потребує ресурсів і часу позбирати
# то лайнецо за попередні місяці та роки.

root_dir = Path(__file__).parent.parent.absolute()
sys.path.append(str(root_dir))

import config
from service.storage.FileCacher import FileCacheManager
from service.storage.StorageFactory import StorageFactory
from service.storage.LoggerManager import LoggerManager

if __name__ == '__main__':
    log_manager = LoggerManager()
    client = StorageFactory.create_client(config.DOCUMENT_STORAGE_PATH, log_manager)
    manager = FileCacheManager(config.CACHE_FILE_PATH, log_manager)
    manager.build_cache(config.DOCUMENT_STORAGE_PATH)
