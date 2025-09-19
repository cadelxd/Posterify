# Spotify Poster Generator

A program that uses Spotify API to get album details from the entered link and generates a stylized poster for it.

---

## How to Run

### 1. Clone the Repository
git clone https://github.com/your-username/Posterify.git
cd Posterify

### 2. Create and Activate Virtual Environment
python -m venv venv<br>
venv\Scripts\activate<br>

### 3. Install Dependencies
pip install -r requirements.txt

### 4. Set your API Keys
create a .env file in the root directory:<br>
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret

### 5. Run the Program
python posterify.py