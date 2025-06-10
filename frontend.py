import chainlit as cl
import httpx
from chainlit.types import ThreadDict
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def fetch_items():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://127.0.0.1:8001/items/")
            response.raise_for_status()
            logger.debug(f"Inventory response: {response.json()}")
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching items: {e.response.status_code} - {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"Failed to fetch items: {str(e)}")
        raise

async def create_item(name: str, quantity: int, price: float):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://127.0.0.1:8001/items/",
                json={"name": name, "quantity": quantity, "price": price}
            )
            response.raise_for_status()
            item = response.json()
            logger.debug(f"Item created: {item}")
            if not all(key in item for key in ["name", "quantity", "price"]):
                logger.error(f"Invalid item response: {item}")
                raise ValueError("Invalid item response from server")
            return item
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error creating item: {e.response.status_code} - {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"Failed to create item: {str(e)}")
        raise

async def sell_item(name: str, quantity: int):
    try:
        async with httpx.AsyncClient() as client:
            # Find item by name to get item_id
            items_response = await client.get("http://127.0.0.1:8001/items/")
            items_response.raise_for_status()
            items = items_response.json()
            item = next((item for item in items if item["name"].lower() == name.lower()), None)
            if not item:
                raise ValueError(f"Item '{name}' not found")
            
            # Send sale request
            response = await client.post(
                "http://127.0.0.1:8001/sales/",
                json={"item_id": item["id"], "quantity": quantity}
            )
            response.raise_for_status()
            sale = response.json()
            logger.debug(f"Sale recorded: {sale}")
            return sale, item
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error selling item: {e.response.status_code} - {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"Failed to sell item: {str(e)}")
        raise

async def handle_query(customer_name: str, query: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://127.0.0.1:8001/queries/",
                json={"customer_name": customer_name, "query": query}
            )
            response.raise_for_status()
            logger.debug(f"Query response: {response.json()}")
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error handling query: {e.response.status_code} - {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"Failed to handle query: {str(e)}")
        raise

@cl.on_chat_start
async def start():
    await cl.Message(content="Welcome to the Store Management System! Type 'inventory' to view items, 'add <name> <quantity> <price>' to add an item, 'sell <name> <quantity>' to sell an item, or ask a query.").send()

@cl.on_message
async def main(message: cl.Message):
    content = message.content.lower().strip()
    logger.debug(f"Received message: {content}")
    
    if content == "inventory":
        try:
            items = await fetch_items()
            response = "Current Inventory:\n" + "\n".join([f"- {item['name']}: {item['quantity']} units, ${item['price']:.2f}" for item in items]) if items else "Current Inventory: Empty"
            await cl.Message(content=response).send()
        except Exception as e:
            logger.error(f"Inventory fetch failed: {str(e)}")
            await cl.Message(content="Error fetching inventory. Please try again.").send()
    
    elif content.startswith("add "):
        try:
            _, name, quantity, price = content.split()
            quantity = int(quantity)
            price = float(price)
            item = await create_item(name, quantity, price)
            await cl.Message(content=f"Added {item['name']} with {item['quantity']} units at ${item['price']:.2f}").send()
        except ValueError as e:
            logger.error(f"Invalid input: {str(e)}")
            await cl.Message(content="Invalid format. Use: add <name> <quantity> <price>").send()
        except Exception as e:
            logger.error(f"Add item failed: {str(e)}")
            await cl.Message(content=f"Error adding item: {str(e)}").send()
    
    elif content.startswith("sell "):
        try:
            _, name, quantity = content.split()
            quantity = int(quantity)
            sale, item = await sell_item(name, quantity)
            await cl.Message(content=f"Sold {quantity} units of {item['name']} for ${sale['total']:.2f}").send()
        except ValueError as e:
            logger.error(f"Invalid input: {str(e)}")
            await cl.Message(content=f"Invalid format or item not found: {str(e)}. Use: sell <name> <quantity>").send()
        except Exception as e:
            logger.error(f"Sell item failed: {str(e)}")
            await cl.Message(content=f"Error selling item: {str(e)}").send()
    
    else:
        try:
            query_response = await handle_query("User", content)
            await cl.Message(content=query_response["response"]).send()
        except Exception as e:
            logger.error(f"Query failed: {str(e)}")
            await cl.Message(content="Error processing query. Please try again.").send()