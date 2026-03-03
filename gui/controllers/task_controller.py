from gui.services.auth_manager import AuthManager
from gui.services.request_context import RequestContext
from service.docworkflow.TaskService import TaskService
from service.processing.MyWorkFlow import MyWorkFlow
from domain.task import Task

# from service.task.TaskService import TaskService, Task, TASK_STATUS_NEW, TASK_STATUS_IN_PROGRESS, TASK_STATUS_COMPLETED

class TaskController:
    def __init__(self, worklow:MyWorkFlow, auth_manager: AuthManager):
        self.db = worklow.db
        self.workflow = worklow
        self.auth_manager = auth_manager
        self.log_manager = self.workflow.log_manager
        self.logger = self.log_manager.get_logger()

    def get_all_tasks(self, ctx: RequestContext, search_filter = None):
        # self.logger.debug('UI:' + ctx.user_name + ': Забираємо задачі для: ' + str(assignee_id))
        service = TaskService(self.db, ctx)
        return service.get_all_tasks(search_filter)

    def update_task_status(self, ctx: RequestContext, task_id: int, new_status: str):
        # self.logger.debug('UI:' + ctx.user_name + ': Зберігаємо статус задачі: ' + str(task_id) + ' : ' + str(new_status))
        service = TaskService(self.db, ctx)
        return service.change_status(task_id, new_status)

    def save_task(self, ctx: RequestContext, task: Task):
        self.logger.debug('UI:' + ctx.user_name + ': Зберігаємо задачу: ' + str(task.task_subject))
        service = TaskService(self.db, ctx)
        return service.save_task(task)

    def delete_task(self, ctx: RequestContext, task_id: int):
        self.logger.debug('UI:' + ctx.user_name + ': Видаляємо задачу: ' + str(task_id))
        service = TaskService(self.db, ctx)
        service.delete_task(task_id)

    def get_task_by_id(self, ctx: RequestContext, task_id: int) -> Task:
        # self.logger.debug('UI:' + ctx.user_name + ': Отримуємо задачу: ' + str(task_id))
        service = TaskService(self.db, ctx)
        return service.get_task_by_id(task_id)

    def get_my_task_counts(self, ctx: RequestContext) -> tuple[int, int]:
        service = TaskService(self.db, ctx)
        return service.get_task_counts_for_user(ctx.user_id)

    def get_available_users(self):
        return self.auth_manager.get_all_users()

    def get_my_alarms(self, ctx: RequestContext):
        service = TaskService(self.db, ctx)
        return service.get_triggered_alarms(ctx.user_id)