import os
from openai import OpenAI
from dotenv import load_dotenv
from sqlmodel import select
from database import SessionDep
from models import Item, Sale
from datetime import date, datetime
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GOOGLE_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/"
)

async def process_customer_query(query: str) -> str:
    try:
        response = client.chat.completions.create(
            model="gemini-1.5-flash",
            messages=[
                {"role": "system", "content": "You are an AI assistant for a retail store. Respond to the customer's query based ONLY on the store's current inventory, which is provided below. Do not assume or invent items that are not in the inventory. If the query mentions an item not in stock, politely inform the customer that it is not available. Provide details like quantity and price for items in stock. Keep responses concise and professional."},
                {"role": "user", "content": query}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Query processing failed: {str(e)}")
        return "Sorry, I couldn't process your query. Please try again."

async def generate_daily_report(session: SessionDep) -> str:
    try:
        today = date.today()
        logger.debug(f"Generating report for {today}")
        sales = session.exec(select(Sale).where(Sale.sale_date == today)).all()
        items = session.exec(select(Item)).all()
        
        low_stock = [item for item in items if item.quantity < 10]
        
        report = f"Daily Sales Report for {today}\n\n"
        report += "Sales:\n"
        total_sales = 0
        for sale in sales:
            item = session.get(Item, sale.item_id)
            if item:
                report += f"- {item.name}: {sale.quantity} units, Total: ${sale.total:.2f}\n"
                total_sales += sale.total
            else:
                logger.warning(f"Item {sale.item_id} not found for sale")
        report += f"\nTotal Sales: ${total_sales:.2f}\n"
        
        report += "\nLow Stock Items:\n"
        if low_stock:
            for item in low_stock:
                report += f"- {item.name}: {item.quantity} units\n"
        else:
            report += "No low stock items.\n"
        
        logger.debug(f"Raw report: {report}")
        prompt = f"Generate a concise summary of this store report:\n{report}"
        response = client.chat.completions.create(
            model="gemini-1.5-flash",
            messages=[
                {"role": "system", "content": "You are a store manager summarizing daily reports."},
                {"role": "user", "content": prompt}
            ]
        )
        summary = response.choices[0].message.content
        logger.debug(f"Generated summary: {summary}")
        return summary
    except Exception as e:
        logger.error(f"Report generation failed: {str(e)}")
        raise