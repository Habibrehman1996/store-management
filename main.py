from fastapi import FastAPI, HTTPException, Request
from twilio.twiml.messaging_response import MessagingResponse
from database import create_db_and_tables, SessionDep
from models import Item, ItemCreate, Sale, SaleCreate, CustomerQuery, CustomerQueryCreate
from notifications import send_whatsapp_notification, send_email_notification
from ai_agent import process_customer_query, generate_daily_report
from sqlmodel import select
import asyncio
from datetime import date
import logging
import os
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Store Management System")

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.post("/items/", response_model=Item)
async def create_item(item: ItemCreate, session: SessionDep):
    try:
        db_item = Item(**item.dict())
        session.add(db_item)
        session.commit()
        session.refresh(db_item)
        logger.debug(f"Created item: {db_item.name}, Quantity: {db_item.quantity}, Price: ${db_item.price:.2f}")
        return db_item
    except Exception as e:
        logger.error(f"Error creating item: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create item")

@app.get("/items/", response_model=list[Item])
async def read_items(session: SessionDep):
    try:
        items = session.exec(select(Item)).all()
        logger.debug(f"Fetched items: {[item.name for item in items]}")
        return items
    except Exception as e:
        logger.error(f"Error fetching items: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch items")

@app.put("/items/{item_id}", response_model=Item)
async def update_item(item_id: int, item: ItemCreate, session: SessionDep):
    try:
        db_item = session.get(Item, item_id)
        if not db_item:
            raise HTTPException(status_code=404, detail="Item not found")
        for key, value in item.dict().items():
            setattr(db_item, key, value)
        session.add(db_item)
        session.commit()
        session.refresh(db_item)
        logger.debug(f"Updated item: {db_item.name}")
        return db_item
    except Exception as e:
        logger.error(f"Error updating item: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update item")

@app.post("/sales/", response_model=Sale)
async def create_sale(sale: SaleCreate, session: SessionDep):
    try:
        item = session.get(Item, sale.item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        if item.quantity < sale.quantity:
            raise HTTPException(status_code=400, detail="Insufficient stock")
        item.quantity -= sale.quantity
        total = sale.quantity * item.price
        db_sale = Sale(item_id=sale.item_id, quantity=sale.quantity, total=total, sale_date=date.today())
        session.add(db_sale)
        session.add(item)
        session.commit()
        session.refresh(db_sale)
        logger.info(f"Sale recorded: Item {item.name}, Quantity: {sale.quantity}, Total: ${total:.2f}")
        return db_sale
    except Exception as e:
        logger.error(f"Error creating sale: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create sale")

@app.post("/queries/", response_model=CustomerQuery)
async def handle_query(query: CustomerQueryCreate, session: SessionDep):
    try:
        response = await process_customer_query(query.query)
        db_query = CustomerQuery(**query.dict(), response=response)
        session.add(db_query)
        session.commit()
        session.refresh(db_query)
        logger.debug(f"Query processed: {query.query}")
        return db_query
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process query")

@app.get("/daily-report/")
async def daily_report(session: SessionDep):
    logger.info("Starting daily report generation")
    try:
        report = await generate_daily_report(session)
        logger.info(f"Report generated: {report}")
        
        # Attempt WhatsApp notification
        try:
            await send_whatsapp_notification(report)
            logger.info("WhatsApp notification sent successfully")
        except Exception as e:
            logger.error(f"Failed to send WhatsApp notification: {str(e)}", exc_info=True)
        
        # Attempt email notification
        try:
            recipient = os.getenv("SMTP_USERNAME")
            logger.debug(f"Sending email to recipient: {recipient}")
            await send_email_notification("Daily Store Report", report, recipient_email=recipient)
            logger.info("Email notification sent successfully")
        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}", exc_info=True)
        
        logger.info("Daily report processing completed")
        return {"report": report}
    except Exception as e:
        logger.error(f"Daily report failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate daily report: {str(e)}")

@app.post("/bot")
async def bot(request: Request, session: SessionDep):
    try:
        form_data = await request.form()
        logger.debug(f"Received form data: {form_data}")
        incoming_msg = form_data.get("Body")
        sender = form_data.get("From")
        if not incoming_msg or not sender:
            logger.error("Missing Body or From in form data")
            raise HTTPException(status_code=400, detail="Invalid request: Missing Body or From")
        response = await process_customer_query(incoming_msg)
        db_query = CustomerQuery(customer_name=sender, query=incoming_msg, response=response)
        session.add(db_query)
        session.commit()
        twiml = MessagingResponse()
        twiml.message(response)
        logger.debug(f"Sending TwiML response: {str(twiml)}")
        return str(twiml)
    except Exception as e:
        logger.error(f"Error in /bot endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")