from nicegui import ui, run, app
from storage.StorageFactory import StorageFactory
import config
import asyncio
from typing import List


# global variable
app.inbox_state = {'count': 0, 'files': []}

class InboxMonitor:
    def __init__(self, workflow):
        self.log_manager = workflow.log_manager
        app.on_startup(self.start_monitoring)

    async def start_monitoring(self):
        while True:
            try:
                count, files = await run.io_bound(self._fetch_inbox_count)
                app.inbox_state['count'] = count
                app.inbox_state['files'] = files
            except Exception as e:
                self.log_manager.get_logger().error(f"Помилка фонового моніторингу Inbox: {e}")

            await asyncio.sleep(config.CHECK_INBOX_EVERY_SEC)

    def _fetch_inbox_count(self) -> (int, List[str]):
        try:
            client = StorageFactory.create_client(config.INBOX_DIR, self.log_manager)
            with client:
                files = client.list_files(config.INBOX_DIR, silent=True)
                valid_files = [f for f in files if not f.startswith('.')]
                return len(valid_files), valid_files
        except Exception as e:
            return 0, []