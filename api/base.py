from loader import *
from utils import *
from fastapi.responses import JSONResponse
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import hmac
import hashlib
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

WEBHOOK_SECRET = "phrase"

class WebhookData(BaseModel):
    profile_id: str
    username: str
    name: Optional[str] = None
    phone: Optional[str] = None
    records_extended: Optional[List[Dict[str, Any]]] = None
    # Остальные поля по необходимости

class WebhookPayload(BaseModel):
    action: str
    data: WebhookData

def extract_customer_info(data: Dict[str, Any]) -> Dict[str, str]:
    """Извлекает ФИО, телефон и адрес из данных вебхука"""
    customer_info = {
        'ФИО': None,
        'Телефон': None,
        'Адрес доставки': None
    }
    
    # Извлекаем из records_extended
    if data.get('records_extended'):
        for record in data['records_extended']:
            if not isinstance(record, dict):
                continue
                
            name = record.get('name', '').lower()
            value = record.get('value', '')
            
            if 'фио' in name:
                customer_info['ФИО'] = value
            elif 'телефон' in name:
                customer_info['Телефон'] = value
            elif 'адрес' in name:
                customer_info['Адрес доставки'] = value
    
    # Дополняем данными из основных полей, если они есть
    if data.get('name') and not customer_info['ФИО']:
        customer_info['ФИО'] = data['name']
    if data.get('phone') and not customer_info['Телефон']:
        customer_info['Телефон'] = data['phone']
    
    return customer_info

@app.post("/webhook/taplink")
async def handle_taplink_webhook(request: Request):
    try:
        webhook_data = await request.json()
        logger.info(f"Получен вебхук: {webhook_data}")
        
        # Извлекаем нужную информацию
        customer_data = extract_customer_info(webhook_data.get('data', {}))
        logger.info(f"Данные клиента: {customer_data}")
        
        # Здесь можно добавить обработку данных (сохранение в БД и т.д.)
        
        return JSONResponse(content={"status": "success"})
    
    except Exception as e:
        logger.error(f"Ошибка обработки вебхука: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
