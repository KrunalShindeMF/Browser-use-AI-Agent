from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os

from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableSequence

app = FastAPI()

# Initialize LangChain OpenAI chat model
llm = ChatOpenAI(
    model_name="gpt-3.5-turbo",
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0,
    max_tokens=150
)

class ProductInput(BaseModel):
    user_input: str

# Create prompt template with placeholder for user_input
prompt_template = PromptTemplate(
    template="""
Extract product details as JSON from this natural language description:

some routes that you need to decide which one to call on the basis of user input. 

url1 : https://crm.fintegrationai.com/admin/admin/products
url2 : https://crm.fintegrationai.com/admin/admin/products/create

\"\"\"
{user_input}
\"\"\"

Respond only with a valid JSON object with keys:
url: 
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
""",
    input_variables=["user_input"],
)

# Instantiate the JSON output parser
json_parser = JsonOutputParser()

# Compose the chain: prompt -> llm -> output parser
chain = prompt_template | llm | json_parser

@app.post("/extract-product-json")
async def extract_product_json(data: ProductInput):
    try:
        # Invoke the chain with user input
        response = chain.invoke({"user_input": data.user_input})
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
