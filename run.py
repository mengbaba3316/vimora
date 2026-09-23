import uvicorn
from app.config import settings

if __name__ == "__main__":
    from app.main import app
    print(f"生图工作台后端: http://127.0.0.1:{settings.APP_PORT}/api/docs")
    uvicorn.run(app, host="127.0.0.1", port=settings.APP_PORT, log_level="info")
