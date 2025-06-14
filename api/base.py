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
    
    # 1. Извлекаем из records (основные поля формы)
    if data.get('records'):
        for record in data['records']:
            if not isinstance(record, dict):
                continue
                
            title = record.get('title', '').lower()
            value = record.get('value', '')
            
            if 'фио' in title:
                customer_info['ФИО'] = value
            elif 'телефон' in title:
                customer_info['Телефон'] = value
    
    # 2. Извлекаем из records_extended (дополнительные поля)
    if data.get('records_extended'):
        for record in data['records_extended']:
            if not isinstance(record, dict):
                continue
                
            name = record.get('name', '').lower()
            value = record.get('value', '')
            
            if name == 'contacts' and isinstance(value, list):
                for contact in value:
                    if 'фио:' in contact.lower():
                        customer_info['ФИО'] = contact.split(':', 1)[1].strip()
                    elif 'телефон:' in contact.lower():
                        customer_info['Телефон'] = contact.split(':', 1)[1].strip()
            
            if name == 'shipping' and isinstance(value, list):
                for shipping_info in value:
                    if 'адрес:' in shipping_info.lower():
                        customer_info['Адрес доставки'] = shipping_info.split(':', 1)[1].strip()
    
    # 3. Извлекаем из shipping_fields (поля доставки)
    if data.get('shipping_fields'):
        for field in data['shipping_fields']:
            if not isinstance(field, dict):
                continue
                
            key = field.get('key', '')
            value = field.get('value', '')
            
            if key == 'addr1':
                customer_info['Адрес доставки'] = value
    
    # 4. Дополняем данными из основных полей, если они есть
    if data.get('fullname') and not customer_info['ФИО']:
        customer_info['ФИО'] = data['fullname']
    if data.get('phone') and not customer_info['Телефон']:
        customer_info['Телефон'] = data['phone']
    if data.get('shipping', {}).get('addr1') and not customer_info['Адрес доставки']:
        customer_info['Адрес доставки'] = data['shipping']['addr1']
    
    return customer_info

@app.post("/webhook/taplink")
async def handle_taplink_webhook(request: Request):
    try:
        webhook_data = await request.json()
        logger.info(f"Получен вебхук")
        
        # Извлекаем нужную информацию
        if 'data' not in webhook_data:
            raise HTTPException(status_code=400, detail="No data in webhook")
            
        customer_data = extract_customer_info(webhook_data['data'])
        
        logger.info("Данные клиента:")
        logger.info(f"ФИО: {customer_data['ФИО']}")
        logger.info(f"Телефон: {customer_data['Телефон']}")
        logger.info(f"Адрес доставки: {customer_data['Адрес доставки']}")
        
        # Здесь можно добавить обработку данных
        return JSONResponse(content={"status": "success"})
    
    except Exception as e:
        logger.error(f"Ошибка обработки вебхука: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
