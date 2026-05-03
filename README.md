# 🚕 Ride-Hailing Backend (Uber-like System)

A scalable, real-time ride-hailing backend built using **FastAPI**, designed to simulate core functionalities of platforms like Uber/Ola.

This project demonstrates backend engineering concepts including **real-time communication, async processing, driver matching, pricing systems, and state management**.

---

## ✨ Features

### 👤 User & Driver System
- User & Driver registration/login
- Role-based access (USER / DRIVER)
- Driver-specific details (vehicle, license)

---

### 📍 Ride Flow
- Request ride with pickup & drop coordinates
- Multiple vehicle types:
  - 🏍 Bike
  - 🛺 Auto
  - 🚗 Mini Car
  - 🚙 Family Car
- Real-time ride status updates

---

### 💰 Pricing Engine
- Distance-based fare calculation (Haversine formula)
- Vehicle-based pricing multipliers
- Surge pricing (demand vs supply simulation)

---

### ⚡ Real-Time System
- WebSocket-based live updates:
  - Driver assigned
  - Driver on the way
  - Driver arrived
  - Trip started / completed

---

### 🔐 OTP Verification
- OTP generated when driver accepts ride
- Required to start trip (security layer)

---

### 🚗 Driver Matching
- Async background task (Celery)
- Matches nearest available driver based on location

---

### ⭐ Rating System
- User ↔ Driver rating
- Average rating calculation
- Prevent duplicate ratings

---

### 📊 Trip Management
- Trip lifecycle:
  - REQUESTED → DRIVER_ASSIGNED → ONGOING → COMPLETED
- Cancel ride (before driver accepts)
- Trip history & analytics

---

## 🧠 Key Concepts Covered

- System design (ride-hailing architecture)
- Async processing
- Distributed locking (race condition prevention)
- Real-time event handling
- State management
- API design best practices

---

## 🛠 Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: SQLAlchemy (PostgreSQL/SQLite)
- **Real-time**: WebSockets
- **Task Queue**: Celery with Redis (for driver matching)
- **Schema Validation**: Pydantic
- **Auth:** JWT-based authentication

## 🚀 Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/uber_clone.git
cd uber_clone
```

### 2. Set up Environment
```bash
python -m venv venv
source venv/bin/activate  
# On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Run Redis (Required for Matching & Locking)
Ensure Redis is running on your machine:
```bash
redis-server --port 6384
```

### 4. Start the Application
Start the FastAPI server:
```bash
uvicorn main:app --reload --port 8003
```

Start the Celery worker (in a new terminal):
```bash
celery -A app.workers.tasks worker --loglevel=info
```

## 🧪 How to Test

1. Open `test_ui.html` in your browser.
2. **Role 1 (Passenger)**: Register as a "Passenger", login, and "Request a Ride".
3. **Role 2 (Driver)**: Open a new tab, register as a "Driver", and "Accept" the ride using the Trip ID from the passenger's log.
4. **Flow**: Follow the on-screen buttons to update location, verify OTP (displayed in Passenger UI), and complete the trip.

## 📡 API Documentation
Once the server is running, visit:
- Interactive Docs: `http://127.0.0.1:8003/docs`


## 🏗 Project Structure
```text
uber_clone/
├── app/
│   ├── models/      # SQLAlchemy Database Models
│   ├── routes/      # API Endpoints (Auth, Ride, etc.)
│   ├── schemas/     # Pydantic Validation Models
│   ├── services/    # Business Logic (Pricing, OTP, Matching)
│   ├── websocket/   # Connection Management
│   └── workers/     # Celery Background Tasks
├── test_ui.html     # Frontend Test Suite
└── main.py          # App Entry Point
```

## 📌 Future Improvements
Live GPS tracking (maps integration)
Payment gateway integration
Driver route optimization
Demand and price optimization
Time estimation using maps

