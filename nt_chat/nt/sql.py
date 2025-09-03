from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

from lanarky import LangchainRouter
from lanarky.testing import mount_gradio_app
from nt_chat.chain import make_chain

app = mount_gradio_app(FastAPI(title="ConversationChainDemo"))
templates = Jinja2Templates(directory="templates")


@app.get("/")
async def get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


langchain_router = LangchainRouter(
    langchain_url="/chat", langchain_object=make_chain(), streaming_mode=0
)
app.include_router(langchain_router)


# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8338)
