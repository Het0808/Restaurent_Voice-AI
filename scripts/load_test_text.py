"""Bounded Locust text-flow load test; install the `load` extra first."""

import uuid

from locust import HttpUser, between, task


class RestaurantTextUser(HttpUser):
    wait_time = between(1, 3)

    @task(4)
    def greeting(self) -> None:
        self.client.post(
            "/api/v1/conversation/message",
            headers={"X-API-Key": "<CLIENT_API_KEY>"},
            json={"message": "Hello", "conversation_id": str(uuid.uuid4())},
        )

    @task(2)
    def knowledge(self) -> None:
        self.client.post(
            "/api/v1/conversation/message",
            headers={"X-API-Key": "<CLIENT_API_KEY>"},
            json={"message": "What is on the menu?", "conversation_id": str(uuid.uuid4())},
        )

    @task(1)
    def reservation_start(self) -> None:
        self.client.post(
            "/api/v1/conversation/message",
            headers={"X-API-Key": "<CLIENT_API_KEY>"},
            json={
                "message": "Book a table for four tomorrow at 7 PM",
                "conversation_id": str(uuid.uuid4()),
            },
        )
