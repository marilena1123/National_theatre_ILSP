import asyncio
import logging
import time

import cachetools
import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from langchain_core.callbacks import AsyncCallbackHandler
from pydantic import BaseModel
from websockets.exceptions import ConnectionClosedOK

from nt_chat.chain import make_chain
from nt_chat.config import (
    LOGGING_FILE,
    MAX_PARALLEL_CALLS,
    RESPONSE_TIME_OUT,
    USE_CACHE,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename=LOGGING_FILE,
    filemode="a",  # Append mode
)
logger = logging.getLogger(__name__)
# Set the logging level of the openai library to WARNING or higher to ignore INFO and DEBUG messages
logging.getLogger("httpx").setLevel(logging.WARNING)

cache = cachetools.LRUCache(maxsize=800)
# Initialize semaphore
print("MAX_PARALLEL_CALLS:", MAX_PARALLEL_CALLS)
concurrent_calls_semaphore = asyncio.Semaphore(MAX_PARALLEL_CALLS)
semaphore_timeout = 0.1


def get_cached_response(user_input):
    """Retrieves response from cache"""
    return cache.get(user_input, None)


def cache_response(user_input, response):
    """Adds response to cache"""
    cache[user_input] = response


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryInput(BaseModel):
    query: str


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/chat")
async def chat_endpoint(input_data: QueryInput):
    """Main chat function"""
    query = input_data.query
    try:
        logger.info("Processing query %s", query)
        start_time = time.time()

        chain = make_chain(stream=True)
        result = await chain.acall(query)

        end_time = time.time()
        logger.info("Completed LLM calls in %s seconds.", end_time - start_time)

        if not result or "result" not in result:
            logger.error("chain.acall returned an unexpected result: %s", result)
            raise HTTPException(
                status_code=500, detail="Internal server error during chain processing."
            )

        answer = result["result"]
        logger.info("Query: %s", query)
        logger.info("Answer: %s", answer)
        return {"answer": answer}
    except Exception as e:
        logger.error("An error occurred: %s", e)
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {e}"
        ) from e


class ChainStreamHandler(AsyncCallbackHandler):
    def __init__(self, ws):
        super().__init__()
        self.ws = ws

    async def on_llm_new_token(self, token: str, **kwargs):
        if "FINAL_RESULT" in kwargs.get("tags", []):
            await self.ws.send_text(token)


@app.websocket("/chatstream")
async def websocket_endpoint(websocket: WebSocket):
    """Main chat endpoint (streaming)"""
    await websocket.accept()
    chain = make_chain(stream=True, return_intermediate_steps=True)
    while True:
        try:
            # Receive client message
            user_msg = await websocket.receive_text()
            logger.info("User request: %s", user_msg)
            if USE_CACHE:
                # Check if the response is already cached
                # Of course this approach is simplistic, it only does string matching
                # For a more sophisticated approach, we can generate embeddings for
                # each user_msg and compare it against the cache
                cached_response = get_cached_response(user_msg)  # .lower())
                if cached_response is not None:
                    logger.info("Found cached response: %s", cached_response)
                    await websocket.send_text(cached_response)
                    continue

            acquired_semaphore = await asyncio.wait_for(
                concurrent_calls_semaphore.acquire(), timeout=semaphore_timeout
            )

            if not acquired_semaphore:
                raise asyncio.TimeoutError()

            # to check the API status: https://status.openai.com/
            # This also sends back the response
            out = await asyncio.wait_for(
                chain.acall(user_msg, callbacks=[ChainStreamHandler(websocket)]),
                timeout=RESPONSE_TIME_OUT,
            )
            sql_query = (
                out["intermediate_steps"][0]["input"]
                .split("\nSQLQuery:")[1]
                .split("\nSQLResult:")[0]
                .strip()
            )
            logger.info("SQL query:\n %s", sql_query)

            if USE_CACHE:
                # Cache the processed response user_msg.lower()
                cache_response(user_msg, out["result"])
            logger.info("Response: %s", out["result"])
            # Send the end-response back to the client and release the semaphore
            await websocket.send_text("[END]")
        except asyncio.TimeoutError:
            await websocket.send_text(
                "Ο ψηφιακός βοηθός είναι στη μέγιστη χωρητικότητα, παρακαλώ δοκιμάστε αργότερα."
            )
            logger.warning("Asyncio.TimeoutError: Service at capacity.")
            break
        except WebSocketDisconnect:
            logger.debug("WebSocket disconnected normally.")
            # Try to reconnect with back-off?
            break
        except ConnectionClosedOK:
            logger.debug("Connection closed normally.")
            break
        except Exception as e:
            logger.error("Unexpected error: %s", e)
            await websocket.send_text("Κάτι πήγε στραβά. Παρακαλώ προσπαθήστε ξανά.")
        finally:
            # Ensure that the semaphore is released in all cases
            if "acquired_semaphore" in locals() and acquired_semaphore:
                concurrent_calls_semaphore.release()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9500)
