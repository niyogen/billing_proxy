from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    wait_time = between(1, 5)

    @task
    def chat_completions(self):
        headers = {
            "Authorization": "Bearer sk-1234", # GATEWAY_TOKEN from docker-compose
            "Content-Type": "application/json"
        }
        data = {
            # Use the new gemini model we added
            "model": "gpt-4o", 
            "messages": [
                {"role": "user", "content": "Hello, assume this is a load test. Reply with 'pong'."}
            ]
        }
        
        with self.client.post("/chat/completions", json=data, headers=headers, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}, Response: {response.text}")
