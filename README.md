# 🚀 ConsistencyAI

**ConsistencyAI** is a full-stack productivity and habit tracking application designed to help users build consistent daily routines, track goals, maintain streaks, and review personal progress over time.

---

## ✨ Features

* 🔐 JWT-based user authentication
* 📝 Daily task management
* 🎯 Goal tracking system
* 🔥 Consistency streaks
* 📊 Progress and reporting dashboard
* 📚 Life rules / habit framework
* 🤖 AI-ready service architecture
* ⚡ Modern responsive React UI

---

## 🛠️ Tech Stack

### Frontend

* React
* TypeScript
* Vite
* CSS

### Backend

* Flask
* SQLAlchemy
* Flask-CORS
* JWT Authentication

### Database

* SQLite (development)

---

## 📂 Project Structure

```text
consistency-ai/
├── backend/          # Flask API
├── frontend/         # React + TypeScript app
├── database/         # SQL migration scripts
├── .env.example      # Environment configuration template
└── README.md
```

---

## ⚙️ Run Locally

### 1️⃣ Clone the repository

```bash
git clone https://github.com/EMBADIANAND/consistency-ai.git
cd consistency-ai
```

### 2️⃣ Start the Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m app.main
```

Backend runs at:

```text
http://127.0.0.1:5000
```

### 3️⃣ Start the Frontend

Open a new terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at:

```text
http://localhost:5173
```

---

## 📡 API Example

### Register a User

```http
POST /api/v1/auth/register
Content-Type: application/json
```

```json
{
  "display_name": "Anand",
  "email": "anand@example.com",
  "password": "StrongPass123"
}
```

---

## 🧪 Development Status

* [x] Authentication API
* [x] React frontend shell
* [x] SQLite integration
* [x] GitHub repository setup
* [ ] Production deployment
* [ ] Persistent cloud database
* [ ] AI coaching integration

---

## 📌 Author

**Anand Embadi**

* GitHub: https://github.com/EMBADIANAND
* LinkedIn: https://www.linkedin.com/in/anand-embadi-7648082a3

---

## ⭐ Support

If you found this project useful, consider giving it a **star ⭐** on GitHub.
