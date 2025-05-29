import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
from langchain_openai import ChatOpenAI
from browser_use import Agent

app = FastAPI()

# Define input model for your API
class ProductRequest(BaseModel):
    email: str
    password: str
    product_name: str
    SKU: str
    price: float
    description: str

@app.post("/create-product")
async def create_product(req: ProductRequest):
    task = f"""
    Please log in to https://crm.fintegrationai.com/admin/login using the following credentials:
    Email: {req.email}
    Password: {req.password}
    After successful login, redirect to the dashboard page https://crm.fintegrationai.com/admin/dashboard

    route :  https://crm.fintegrationai.com/admin/admin/products/create desc : For create product
    route :  https://crm.fintegrationai.com/admin/admin/products  desc : For product listing
    Please make sure to fill all the required fields like product name, category, price, description, and quantity. and other if required fields.

    Product details:
    Name: {req.product_name}
    Price: {req.price}
    Description: {req.description}
    SKU: {req.SKU}

    After completing all these processes just return the message like "Product created successfully!". or any other process which completed and along with that just add last page url as well.
    response in json format like this:

    {{
        "message": "Product created successfully!",
        "last_page_url": "https://crm.fintegrationai.com/admin/admin/products"
    }}
    """

    agent = Agent(task=task, llm=ChatOpenAI(model="gpt-4o"))

    try:
        result = await agent.run()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent run failed: {e}")

    # Extract last done message and last navigated url as before
    last_message = None
    last_url = None
    for action in reversed(result.all_results):
        if action.is_done and action.success:
            last_message = action.extracted_content
            break
    for action in reversed(result.all_results):
        if action.extracted_content and action.extracted_content.startswith("🔗  Navigated to"):
            last_url = action.extracted_content.split(" to ")[-1].strip()
            break

    response = {
        "message": last_message or "No completion message found",
        "last_page_url": last_url or "No URL found"
    }

    return response
