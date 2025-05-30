# =================================== Demo ===================================
import asyncio
import json, sys
from dotenv import load_dotenv
load_dotenv()
from browser_use import Agent
from langchain_openai import ChatOpenAI

async def main():
    agent = Agent(
        task="""Please log in to https://crm.fintegrationai.com/admin/login using the following credentials:
                Email: admin@example.com                Password: admin123
                After successful login, redirect to the dashboard page https://crm.fintegrationai.com/admin/dashboard

                After that, from this route https://crm.fintegrationai.com/admin/admin/products/create create a product with necessary details for product creation,
                Then prodcut should be listed in this https://crm.fintegrationai.com/admin/admin/products page with the popup message like product created successfully.
                Please make sure to fill all the required fields like product name, category, price, description, and quantity.

                After completing all these processes just return the message like "Product created successfully!". or any other process which completed and alongwith that just add last page url as well.
                response in json format like this:

                {
                    "message": "Product created successfully!",
                    "last_page_url": "https://crm.fintegrationai.com/admin/admin/products"
                }
                
                """,
        llm=ChatOpenAI(model="gpt-4o"),
    )
    result = await agent.run()

    print(" Result  : ", result)

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
        "message": last_message or "No message found",
        "last_page_url": last_url or "No URL found"
    }

    print(json.dumps(response, indent=4))

asyncio.run(main())