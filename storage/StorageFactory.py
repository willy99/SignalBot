from storage.FileStorageClient import FileStorageClient
from storage.LocalFileClient import LocalFileClient
from storage.SMBFileClient import SMBFileClient

class StorageFactory:
    @staticmethod
    def create_client(path: str) -> FileStorageClient:
        if path.startswith("\\\\"):
            return SMBFileClient()
        else:
            return LocalFileClient()