import os
import uvicorn
from web_app import app
from config import WEB_HOST, WEB_PORT

if __name__ == "__main__":
    port = int(os.getenv("PORT", WEB_PORT))
    print(f"🚀 Admin Web App va CMS serveri ishga tushmoqda: 0.0.0.0:{port}")
    uvicorn.run("web_app:app", host="0.0.0.0", port=port, log_level="info")
