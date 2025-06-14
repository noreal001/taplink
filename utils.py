
from fastapi import HTTPException
from dotenv import load_dotenv
from functools import wraps
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
import httpx
import logging
load_dotenv()

# Настроим логирование
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def exception_handler(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            logging.info("inside wrapper of exception handler")
            return await func(*args, **kwargs)
        except HTTPException as e:
            logging.error(f"HTTP error: {e.detail}")
            return JSONResponse({"status": "error", "message": e.detail}, status_code=e.status_code)
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            return JSONResponse({"status": "error", "message": "Internal server error"}, status_code=500)
    return wrapper


async def send_request(url: str, data: dict, method: str = "POST") -> dict:
    """Универсальная функция для отправки HTTP-запросов с обработкой ошибок."""
    try:
        async with httpx.AsyncClient() as client:
            if method.upper() == "POST":
                response = await client.post(url, json=data)
            elif method.upper() == "GET":
                response = await client.get(url, params=data)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()  # Проверка на ошибки HTTP

            logging.info(f"Запрос на {url} успешно отправлен.")
            return response.json()  # Возвращаем данные ответа в формате JSON

    except httpx.RequestError as e:
        logging.error(f"Ошибка при отправке запроса: {e}")
        raise HTTPException(status_code=500, message="Request failed")

    except httpx.HTTPStatusError as e:
        logging.error(f"Ошибка HTTP при отправке запроса: {e}")
        raise HTTPException(status_code=500, message=f"HTTP error: {e.response.status_code}")

    except Exception as e:
        logging.error(f"Неизвестная ошибка: {e}")
        raise HTTPException(status_code=500, message="An unknown error occurred")