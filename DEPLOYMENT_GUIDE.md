# 24/7 Cloud Hosting Guide for Destination Unlimited Travels

When your laptop is turned off or in sleep mode, local software cannot receive internet requests. To make your system run **24 hours a day, 7 days a week, 365 days a year** without needing your laptop, host it on a cloud server.

---

## 🚀 Method 1: Render.com (Easiest & Free)

1. Sign up for a free account at **[https://render.com](https://render.com)**.
2. Click **New +** → **Web Service**.
3. Choose **Deploy an existing image** or connect your GitHub repository containing this folder.
   - If uploading directly, you can zip `visa-doc-system` and push to GitHub.
4. Settings:
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Click **Create Web Service**.
6. You will receive a permanent 24/7 link like:
   `https://destination-unlimited.onrender.com/upload-documents`

---

## 🐍 Method 2: PythonAnywhere (No Git Required)

1. Create a free account at **[https://www.pythonanywhere.com](https://www.pythonanywhere.com)**.
2. Go to the **Files** tab and upload the `visa-doc-system` zip folder.
3. Open a **Bash Console** and run:
   ```bash
   pip install -r requirements.txt
   ```
4. In the **Web** tab, configure the WSGI/ASGI file to point to `app.main:app`.
5. Your system will run 24/7 at:
   `https://yourusername.pythonanywhere.com/upload-documents`

---

## 🌐 Method 3: Cloud VPS with Your Own Custom Domain

If you have a domain like `destinationunlimitedtravels.com`:
1. Get a basic Linux VPS ($4/month on DigitalOcean, Hetzner, or Hostinger).
2. Copy this folder onto the VPS.
3. Run with `docker-compose` or `systemd` (background daemon).
4. Clients can visit:
   `https://destinationunlimitedtravels.com/upload-documents`
