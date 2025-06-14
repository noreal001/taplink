from fastapi.responses import JSONResponse
from config import PORT
import uvicorn
from api.base import *
from utils import *

@app.api_route("/", methods=["GET", "HEAD"])
async def super(request: Request):
    return JSONResponse(content={"message": "Супер"}, status_code=200, headers={"Content-Type": "application/json; charset=utf-8"})

# Основной запуск FastAPI
if __name__ == "__main__":
    port = int(PORT)  # Порт будет извлечен из окружения или 8000 по умолчанию
    uvicorn.run(app, host="0.0.0.0", port=port)
