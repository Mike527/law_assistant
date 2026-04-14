import uvicorn
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
# import os
# os.environ["HTTP_PROXY"] = "http://localhost:7890"
# os.environ["HTTPS_PROXY"] = "http://localhost:7890"

# ==========================================
# 1. API 配置 (这里以 DeepSeek 为例)
# 你可以轻松换成其他模型，只需更改以下三个变量
# ==========================================
API_KEY = "sk-5e3049ac148e405bb0b6c9fd11111add"
API_URL = "https://api.deepseek.com" 
MODEL_NAME = "deepseek-chat"

# ==========================================
# 2. 初始化 FastAPI 应用与跨域配置
# ==========================================
app = FastAPI(title="法知明 - 劳动纠纷助手后端 (httpx 版)")

# 允许跨域请求，确保前端 fetch 不会报错
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 3. 定义数据模型
# ==========================================
class MessageItem(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    user_id: str
    message: str
    chat_history: List[MessageItem] = []

# ==========================================
# 4. 核心对话接口
# ==========================================
SYSTEM_PROMPT = """你是一个名为“法知明”的专业劳动者权益法律咨询助手。
你的目标是：
1. 态度温暖、专业，像朋友一样安抚用户的情绪。
2. 准确引用《中华人民共和国劳动法》、《劳动合同法》等相关法律条款。
3. 给出实用的维权建议（如收集什么证据、如何去劳动监察大队投诉、如何申请仲裁）。
4. 如果用户提供的信息不足，主动向用户提问（如：是否有签订书面合同？每月工资多少？）。
5. 你的回答将直接显示在网页聊天框中，请使用换行符和简单的符号表情（如✅、📌）进行排版，避免长篇大论。"""

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    # 1. 组装消息历史
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in req.chat_history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": req.message})

    # 2. 构造 HTTP 请求的 Headers 和 Payload
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1000
    }

    # 3. 使用 httpx 发起异步原生网络请求
    # 设置 timeout=60 防止大模型生成较慢时请求超时
    async with httpx.AsyncClient(timeout=60.0, proxies="http://127.0.0.1:7897") as client:
        try:
            response = await client.post(API_URL, json=payload, headers=headers)
            
            # 检查 HTTP 状态码，如果不是 200 会抛出异常
            response.raise_for_status() 
            
            # 解析 JSON 响应
            resp_data = response.json()
            ai_reply = resp_data["choices"][0]["message"]["content"]
            
            # 返回前端期望的格式
            return {"response": ai_reply}
            
        except httpx.HTTPStatusError as e:
            # 捕获 4xx/5xx 状态码错误 (例如 API Key 错误或余额不足)
            error_msg = e.response.text
            print(f"API 状态码错误: {e.response.status_code} - {error_msg}")
            raise HTTPException(status_code=500, detail="大模型接口鉴权失败或服务异常，请检查 API Key。")
            
        except httpx.RequestError as e:
            # 捕获网络连接错误 (例如断网或 URL 写错)
            print(f"网络请求报错: {str(e)}")
            raise HTTPException(status_code=500, detail="无法连接到大模型服务器，请检查网络。")
            
        except Exception as e:
            # 捕获其他未知错误
            print(f"未知后端报错: {str(e)}")
            raise HTTPException(status_code=500, detail="服务器内部错误，请稍后再试。")

# ==========================================
# 5. 挂载静态文件目录
# ==========================================
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)