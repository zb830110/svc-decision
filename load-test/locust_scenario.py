from locust import HttpLocust, TaskSet, task

class BackendBehavior(TaskSet):
    @task(59)
    def get_sleep(self):
        self.client.get("/control/sleep/1")
    # def get_user_blocker(self):
    #     self.client.get("/v0/user-blocker/45563")

    @task(12)
    def get_ready(self):
        self.client.get("/control/ready")

    @task(12)
    def get_healthy(self):
        self.client.get("/control/healthy")

    @task(6)
    def get_same_day_ach_restore(self):
        self.client.get("/v0/same-day-ACH-restore/45563")

    @task(6)
    def get_max_adjustment(self):
        self.client.get("/v0/max-adjustment/45563")

    @task(4)
    def get_metrics(self):
        self.client.get("/metrics")

    @task(1)
    def get_max_adjustment_act(self):
        self.client.get("/v0/max-adjustment-act/45563")


class LocustRunner(HttpLocust):
    task_set = BackendBehavior
    min_wait = 500
    max_wait = 1000
