from storage.FileStorageClient import FileStorageClient
from storage.LocalFileClient import LocalFileClient
from storage.SMBFileClient import SMBFileClient
from storage.LoggerManager import LoggerManager

class StorageFactory:
    @staticmethod
    def create_client(path: str, log_manager: LoggerManager) -> FileStorageClient:
        if path.startswith("\\\\"):
            return SMBFileClient(path, log_manager)
        else:
            return LocalFileClient(path, log_manager)