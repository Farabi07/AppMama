from django.apps import AppConfig

class TaskConfig(AppConfig):
    name = 'task'

    def ready(self):
        import task.signals  # This imports the signals when the app is ready
        print("Tasks app is ready and signals are imported.")
