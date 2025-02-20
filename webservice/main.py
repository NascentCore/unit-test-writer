import asyncio
import os
import sys
import traceback
from typing import Optional

import aiohttp
from aiohttp import web
import cachetools
from gidgethub import aiohttp as gh_aiohttp
from gidgethub import routing
from gidgethub import sansio
from gidgethub import apps

from dotenv import load_dotenv

# 从.env文件加载环境变量
load_dotenv()

# 配置常量
CACHE_SIZE = 500
DEFAULT_PORT = 8080

router = routing.Router()
cache = cachetools.LRUCache(maxsize=CACHE_SIZE)
routes = web.RouteTableDef()

async def get_installation_token(gh: gh_aiohttp.GitHubAPI, installation_id: int) -> dict:
    """获取GitHub App的安装访问令牌"""
    return await apps.get_installation_access_token(
        gh,
        installation_id=installation_id,
        app_id=os.environ.get("GH_APP_ID"),
        private_key=os.environ.get("GH_PRIVATE_KEY")
    )

@routes.get("/", name="home")
async def handle_get(request: web.Request) -> web.Response:
    """处理首页GET请求"""
    return web.Response(text="Hello PyLadies Tunis")

@routes.post("/webhook")
async def webhook(request: web.Request) -> web.Response:
    """处理GitHub webhook请求"""
    try:
        body = await request.read()
        secret = os.environ.get("GH_SECRET")
        event = sansio.Event.from_http(request.headers, body, secret=secret)
        print(f"收到事件: {event.event}")
        
        if event.event == "ping":
            return web.Response(status=200)
            
        async with aiohttp.ClientSession() as session:
            gh = gh_aiohttp.GitHubAPI(session, "demo", cache=cache)
            await router.dispatch(event, gh)
            
            try:
                print("GH requests remaining:", gh.rate_limit.remaining)
            except AttributeError:
                pass
                
        return web.Response(status=200)
        
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        return web.Response(status=500)

@router.register("installation", action="created")
async def repo_installation_added(event, gh, *args, **kwargs):
    """处理GitHub App安装事件"""
    installation_id = event.data["installation"]["id"]
    installation_token = await get_installation_token(gh, installation_id)
    
    repo_name = event.data["repositories"][0]["full_name"]
    url = f"/repos/{repo_name}/issues"
    
    response = await gh.post(
        url,
        data={
            'title': '感谢安装本机器人',
            'body': '我会为您提供优质的服务!',
        },
        oauth_token=installation_token["token"]
    )
    print(response)

@router.register("pull_request", action="opened")
async def pr_opened(event, gh, *args, **kwargs):
    """处理新的Pull Request被打开的事件"""
    installation_id = event.data["installation"]["id"]
    installation_token = await get_installation_token(gh, installation_id)

    # 获取PR相关信息
    repo_full_name = event.data["repository"]["full_name"]
    pr_number = event.data["pull_request"]["number"]
    
    # 创建评论
    comments_url = f"/repos/{repo_full_name}/issues/{pr_number}/comments"
    await gh.post(
        comments_url,
        data={
            "body": "感谢提交PR！我会尽快审核。"
        },
        oauth_token=installation_token["token"]
    )

if __name__ == "__main__":  # pragma: no cover
    app = web.Application()
    app.router.add_routes(routes)
    
    port = int(os.environ.get("PORT", DEFAULT_PORT))
    web.run_app(app, port=port)
