from tasks.celery_app import celery_app

@celery_app.task(name="tasks.test_task.add")
def add(x, y):
    return x + y