import asyncio
import sys
from concurrent.futures import ThreadPoolExecutor
import nest_asyncio
from typing import Dict, Any, Optional
import re

# Allow nested event loops
nest_asyncio.apply()

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from browser_use import Agent
from langchain_openai import ChatOpenAI
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Define input model for your API
class AgentRequest(BaseModel):
    email: str
    password: str
    user_query: str
    # product_name: str
    # SKU: str
    # price: float
    # description: str

def run_agent_sync(task: str):
    """Run the agent in a separate event loop"""
    async def agent_main():
        agent = Agent(task=task, llm=ChatOpenAI(model="gpt-4o"))
        try:
            result = await agent.run()
            return result
        except Exception as e:
            raise e
    
    # Create a new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(agent_main())
    finally:
        loop.close()

def extract_agent_info(agent_result) -> Dict[str, Any]:
    """
    Extract last navigated URL and success/failure message from agent result
    """
    try:
        # Initialize return values
        last_url = None
        success_message = None
        is_success = False
        
        # Handle different response formats
        if hasattr(agent_result, 'all_results'):
            actions = agent_result.all_results
        elif isinstance(agent_result, (list, tuple)):
            actions = agent_result
        else:
            # Try to convert to string and parse
            result_str = str(agent_result)
            return parse_from_string(result_str)
        
        last_url_candidates = []
        for action in actions:
            content = getattr(action, 'extracted_content', '')
            if '🔗  Navigated to' in content:
                url_match = re.search(r'🔗\s+Navigated to\s+(https?://[^\s]+)', content)
                if url_match:
                    url = url_match.group(1)
                    last_url_candidates.append(url)
    
        # Filter URLs: exclude login and creation pages
        filtered_urls = [url for url in last_url_candidates if 'login' not in url.lower() and 'create' not in url.lower()]
        if filtered_urls:
            last_url = filtered_urls[-1]
        else:
            last_url = last_url_candidates[-1] if last_url_candidates else None
        
        return {
            "last_navigated_url": last_url or "No URL found",
            "success": is_success,
            "message": success_message or "No completion message found",
            "status": "success" if is_success else "failed"
        }
        
    except Exception as e:
        return parse_from_string(str(agent_result))

def parse_from_string(result_str: str) -> Dict[str, Any]:
    """
    Fallback parser for string representation of agent result
    """
    try:
        # Extract URLs
        url_pattern = re.compile(r"🔗\s+Navigated to\s+(https?://[^\s,'\"\}]+)")
        urls = url_pattern.findall(result_str)
        last_url = urls[-1] if urls else None
        
        # Clean up URL if it has trailing characters
        if last_url:
            last_url = re.sub(r'[,\'\"\}]+$', '', last_url)
        
        # Extract success/failure information
        success = False
        message = "No message found"
        
        # Look for success indicators
        success_patterns = [
            r"'success':\s*True",
            r'"success":\s*true',
            r"Successfully.*?(?='|\"|\})",
            r"success.*?completed"
        ]
        
        for pattern in success_patterns:
            if re.search(pattern, result_str, re.IGNORECASE):
                success = True
                break
        
        # Extract the actual success message
        message_patterns = [
            r"Successfully[^'\"]*",
            r"'text':\s*['\"]([^'\"]+)['\"]",
            r'"text":\s*"([^"]+)"',
            r"completed.*?['\"]([^'\"]*)['\"]"
        ]
        
        for pattern in message_patterns:
            match = re.search(pattern, result_str, re.IGNORECASE)
            if match:
                if match.groups():
                    message = match.group(1)
                else:
                    message = match.group(0)
                break
        
        return {
            "last_navigated_url": last_url or "No URL found",
            "success": success,
            "message": message,
            "status": "success" if success else "failed"
        }
        
    except Exception as e:
        return {
            "last_navigated_url": "Error parsing URL",
            "success": False,
            "message": f"Error parsing result: {str(e)}",
            "status": "error"
        }

def clean_and_extract_final_result(result_str: str) -> Dict[str, Any]:
    """
    Clean the malformed result and extract key information
    """
    try:
        # Find the last occurrence of a complete success message
        success_pattern = r"Successfully logged in to the CRM and created the product[^'\"]*"
        success_matches = re.findall(success_pattern, result_str, re.IGNORECASE)
        
        if success_matches:
            success_message = success_matches[-1].strip()
            success = True
        else:
            success_message = "Task completion status unclear"
            success = False
        
        # Extract the last navigated URL
        url_pattern = r"https://crm\.fintegrationai\.com[^\s,'\"]*"
        urls = re.findall(url_pattern, result_str)
        
        # Filter out login URL, prefer create/dashboard URLs
        filtered_urls = [url for url in urls if 'login' not in url]
        last_url = filtered_urls[-1] if filtered_urls else (urls[-1] if urls else None)
        
        return {
            "last_navigated_url": last_url or "No URL found",
            "success": success,
            "message": success_message,
            "status": "success" if success else "failed"
        }
        
    except Exception as e:
        return {
            "last_navigated_url": "Error parsing",
            "success": False,
            "message": f"Parsing error: {str(e)}",
            "status": "error"
        }

def extract_info_from_text(log_text: str):
    import re

    url_pattern = re.compile(r"🔗\s+Navigated to\s+(https?://[^\s]+)")
    urls = url_pattern.findall(log_text)
    last_url = urls[-1] if urls else "No URL found"

    message_pattern = re.compile(r".*(successfully|success|failed|error|done|completed).*", re.IGNORECASE)

    lines = log_text.strip().splitlines()
    last_message = None
    for line in reversed(lines):
        if message_pattern.match(line):
            last_message = line.strip()
            break

    if not last_message:
        last_message = "\n".join(lines[-3:]) if len(lines) >= 3 else "\n".join(lines)

    return {
        "last_page_url": last_url,
        "message": last_message,
    }

@app.post("/run-agent")
async def run_agent(req: AgentRequest):

    email = req.email
    password = req.password
    user_query = req.user_query

    task = f"""
    Please log in to https://crm.fintegrationai.com/admin/login using the following credentials:
    Email: {email}
    Password: {password}
    After successful login, redirect to the dashboard page https://crm.fintegrationai.com/admin/dashboard

    route :  https://crm.fintegrationai.com/admin/admin/products/create desc : For create product
    route :  https://crm.fintegrationai.com/admin/admin/products desc : For product listing

    user_query: {user_query}
    
    After completing all these processes, return the full agent history
    """

    try:
        # Run the agent in a thread pool to avoid event loop conflicts
        with ThreadPoolExecutor() as executor:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(executor, run_agent_sync, task)

        print(result)
        
        # Use the improved extraction function
        extracted_info = extract_agent_info(result)
        
        # If the main extraction fails, try string parsing as fallback
        if extracted_info["last_navigated_url"] == "No URL found":
            extracted_info = clean_and_extract_final_result(str(result))

        return {
            "summary": extracted_info,
            "last_navigated_url": extracted_info["last_navigated_url"],
            "success": extracted_info["success"],
            "message": extracted_info["message"],
            "status": extracted_info["status"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent run failed: {str(e)}")