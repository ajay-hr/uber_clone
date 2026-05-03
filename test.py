import pytest
import httpx
import asyncio
# import websockets # Mocked for testing
import json
from unittest.mock import patch, MagicMock

BASE_URL = "http://127.0.0.1:8003"
WS_URL = "ws://127.0.0.1:8003"

driver_id = None
user_id = None
trip_id = None


@pytest.mark.asyncio
@patch("app.services.kafka_producer.send_ride_request_event")
@patch("app.services.matching_service.acquire_lock", return_value=True)
@patch("app.services.matching_service.release_lock")
@patch("app.workers.tasks.match_driver_task.delay")
@patch("websockets.connect", new_callable=MagicMock)
async def test_full_uber_flow(mock_ws, mock_match, mock_release, mock_acquire, mock_kafka):
    global driver_id, user_id, trip_id

    async with httpx.AsyncClient() as client:

        # -------------------------
        # 1. Register Driver
        # -------------------------
        res = await client.post(f"{BASE_URL}/auth/register", json={
            "name": "Driver3",
            "email": "driver3@test.com",
            "password": "123456",
            "role": "DRIVER"
        })
        assert res.status_code == 200
        driver_id = res.json()["id"]
        print("Driver ID:", driver_id)

        # -------------------------
        # 2. Register User
        # -------------------------
        res = await client.post(f"{BASE_URL}/auth/register", json={
            "name": "User2",
            "email": "user2@test.com",
            "password": "123456",
            "role": "USER"
        })
        assert res.status_code == 200
        user_id = res.json()["id"]
        print("User ID:", user_id)

        # -------------------------
        # 3. Connect WebSocket (Driver Location)
        # -------------------------
        # Mocking WS interaction
        ws = MagicMock()
        ws.send = MagicMock(side_effect=lambda x: None)
        ws.close = MagicMock(side_effect=lambda: None)

        await asyncio.sleep(1)  # allow Redis update

        # -------------------------
        # 4. Request Ride
        # -------------------------
        res = await client.post(f"{BASE_URL}/ride/request", json={
            "user_id": user_id,
            "pickup_lat": 28.61,
            "pickup_lng": 77.23,
            "drop_lat": 28.70,
            "drop_lng": 77.10
        })
        assert res.status_code == 200
        trip_id = res.json()["trip_id"]
        print("Trip ID:", trip_id)

        # wait for celery matching
        await asyncio.sleep(2)

        # -------------------------
        # 5. Accept Ride
        # -------------------------
        res = await client.post(f"{BASE_URL}/ride/accept", json={
            "trip_id": trip_id,
            "driver_id": driver_id
        })
        assert res.status_code == 200
        print("Ride accepted")

        # -------------------------
        # 6. Start Trip
        # -------------------------
        res = await client.post(f"{BASE_URL}/ride/start", json={
            "trip_id": trip_id,
            "user_id": driver_id
        })
        assert res.status_code == 200
        print("Trip started")

        # -------------------------
        # 7. End Trip
        # -------------------------
        res = await client.post(f"{BASE_URL}/ride/end", json={
            "trip_id": trip_id,
            "user_id": driver_id
        })
        assert res.status_code == 200
        assert "fare" in res.json()
        print("Trip ended, Fare:", res.json()["fare"])

        # -------------------------
        # 8. Rate Trip
        # -------------------------
        res = await client.post(f"{BASE_URL}/ride/rate", json={
            "trip_id": trip_id,
            "rater_id": user_id,
            "ratee_id": driver_id,
            "rating_type": "DRIVER",
            "score": 5,
            "comment": "Great ride!"
        })
        assert res.status_code == 200
        print("Rating submitted")

        # Assertions for mocks
        mock_kafka.assert_called_once()