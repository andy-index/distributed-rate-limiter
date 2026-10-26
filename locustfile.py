from locust import HttpUser, task, between

class RateLimitUser(HttpUser):
	wait_time = between(0.1,0.5)

	@task
	def hit_endpoint(self):
		with self.client.get("/", catch_response=True) as response:
			#429 is correct behavior, not a failure
			if response.status_code in (200, 429):
				response.success()
