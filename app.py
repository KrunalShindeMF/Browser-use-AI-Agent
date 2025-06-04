

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import openai
import os
import json

openai.api_key = os.getenv("OPENAI_API_KEY")  # Set your OpenAI API key as an environment variable

app = FastAPI()

class ProductInput(BaseModel):
    user_input: str

@app.post("/extract-product-json")
async def extract_product_json(data: ProductInput):
    prompt = f"""
Extract product details as JSON from this natural language description:

some routes that you need to decide which one to call on the basis of user input. 

url1 : https://crm.fintegrationai.com/admin/admin/products
url2 : https://crm.fintegrationai.com/admin/admin/products/create

\"\"\"
{data.user_input}
\"\"\"

Respond only with a valid JSON object with keys:
name:
description:
sku:
price:

Example:
{{
  "url": "https://crm.fintegrationai.com/admin/admin/products/create",
  "name": "Chat-v1",
  "description": "We can integrate this product with any website.",
  "sku": "V10001",
  "price": "$5"
}}
"""

    try:
        response = openai.Completion.create(
            model="gpt-3.5-turbo",
            prompt=prompt,
            max_tokens=150,
            temperature=0,
            stop=None
        )
        text = response.choices[0].text.strip()

        # Try to parse JSON from the response
        try:
            product_json = json.loads(text)
        except json.JSONDecodeError:
            # If response is not clean JSON, raise error or return raw text
            raise HTTPException(status_code=500, detail="Failed to parse JSON from OpenAI response")

        return product_json

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
