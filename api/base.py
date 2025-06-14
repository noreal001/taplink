from loader import *
from utils import *
from fastapi.responses import JSONResponse
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import hmac
import hashlib
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import requests
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime

WEBHOOK_SECRET = "phrase"
# Конфигурация СДЭК API
CDEK_API_URL = "https://api.cdek.ru/v2/orders"
CDEK_AUTH_URL = "https://api.cdek.ru/v2/oauth/token"
CDEK_CLIENT_ID = "FUqoYOueA6E1WwpC4VfnnqIKSHQOaIuw"  # Замените на реальные данные
CDEK_CLIENT_SECRET = "q2x8JzZbLgpezQxpqhhrRHJk1yrP5lxh"  # Замените на реальные данные

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

class CDEKAuthResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    scope: str
    jti: str

class CDEKOrderResponse(BaseModel):
    uuid: Optional[str] = None
    order_number: Optional[str] = None
    error: Optional[str] = None

def get_cdek_auth_token() -> str:
    """Получение токена авторизации для СДЭК API"""
    try:
        response = requests.post(
            CDEK_AUTH_URL,
            data={
                'grant_type': 'client_credentials',
                'client_id': CDEK_CLIENT_ID,
                'client_secret': CDEK_CLIENT_SECRET
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        response.raise_for_status()
        auth_data = CDEKAuthResponse(**response.json())
        return auth_data.access_token
    except Exception as e:
        logger.error(f"Ошибка получения токена СДЭК: {str(e)}")
        raise

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

def create_cdek_order(customer_data: Dict[str, str], order_number: str) -> Dict[str, Any]:
    """Создание заказа в СДЭК"""
    try:
        logger.info("create_cdek_order вызван")
        
        token = get_cdek_auth_token()

        logger.info("token")
        logger.info(token)
        
        order_data = {
            "type": 1,  # Тип заказа: "доставка"
            "number": order_number,
            "tariff_code": 136,  # Код тарифа: "Посылка склад-склад"
            "sender": {
                "company": "Название вашей компании",
                "name": "Контактное лицо",
                "phones": [{"number": "+79999999999"}]
            },
            "recipient": {
                "name": customer_data['ФИО'],
                "phones": [{"number": customer_data['Телефон']}]
            },
            "to_location": {
                "address": customer_data['Адрес доставки']
            },
            "packages": [{
                "number": f"{order_number}-1",
                "weight": 0,  # Вес в граммах
                "length": 0,  # Длина в мм
                "width": 0,   # Ширина в мм
                "height": 0  # Высота в мм
            }]
        }

        
        logger.info("order_data")
        logger.info(order_data)
        
        response = requests.post(
            CDEK_API_URL,
            json=order_data,
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
        )

        logger.info("response")
        logger.info(response)
        
        if response.status_code != 200:
            error_msg = f"СДЭК API ошибка: {response.status_code} - {response.text}"
            logger.error(error_msg)
            return {"error": error_msg}
        
        return response.json()
    except Exception as e:
        logger.error(f"Ошибка создания заказа в СДЭК: {str(e)}")
        return {"error": str(e)}


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
        
        # Создаем заказ в СДЭК
        order_number = customer_data.get('order_number', f"order-{datetime.now().strftime('%Y%m%d%H%M%S')}")
        cdek_response = create_cdek_order(customer_data, order_number)
        
        if 'error' in cdek_response:
            raise HTTPException(status_code=400, detail=cdek_response['error'])
        
        logger.info(f"Заказ в СДЭК создан: {cdek_response}")
        return JSONResponse(content={
            "status": "success",
            "cdek_order": cdek_response
        })
    
    except Exception as e:
        logger.error(f"Ошибка обработки вебхука: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
