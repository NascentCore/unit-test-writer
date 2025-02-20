import asyncio
import os
import sys
import traceback


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


router = routing.Router()
cache = cachetools.LRUCache(maxsize=500)

routes = web.RouteTableDef()


@routes.get("/", name="home")
async def handle_get(request):
    return web.Response(text="Hello PyLadies Tunis")


@routes.post("/webhook")
async def webhook(request):
    try:
        body = await request.read()
        secret = os.environ.get("GH_SECRET")
        event = sansio.Event.from_http(request.headers, body, secret=secret)
        print(f"收到事件: {event.event}")
        if event.event == "ping":
            return web.Response(status=200)
        async with aiohttp.ClientSession() as session:
            gh = gh_aiohttp.GitHubAPI(session, "demo", cache=cache)

            await asyncio.sleep(1)
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
    installation_id = event.data["installation"]["id"]

    installation_access_token = await apps.get_installation_access_token(
        gh,
        installation_id=installation_id,
        app_id=os.environ.get("GH_APP_ID"),
        private_key=os.environ.get("GH_PRIVATE_KEY")
    )
    repo_name = event.data["repositories"][0]["full_name"]
    url = f"/repos/{repo_name}/issues"
    response = await gh.post(
        url,
                     data={
        'title': 'Thanks for installing my bot',
        'body': 'Thanks!',
            },
        oauth_token=installation_access_token["token"]
                             )
    print(response)


@router.register("pull_request", action="opened")
async def pr_opened(event, gh, *args, **kwargs):
    """处理新的Pull Request被打开的事件"""
    installation_id = event.data["installation"]["id"]
    
    installation_access_token = await apps.get_installation_access_token(
        gh,
        installation_id=installation_id,
        app_id=os.environ.get("GH_APP_ID","1151730"),
        private_key=os.environ.get("GH_PRIVATE_KEY","""-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAqpq97S9x6hkjWhezsHa0UENJ5Bjt65R0bq4Hu+cwCsUwMURg
le8+dMpVbBYgdqhmB1/kQlTUceyjbHufr3NZOSlxPdDtzfQCMF11FkyFW5dQKhYg
d7mpgWK8odjn75ZeHXrcNR5CW8C0eAwFtu5oeDfD6i/GrpCoewCFwpDhEcYuSTww
d7Exg5IbJUqdhWA46DJIMA3QlOJ6WSvbZ9DWfZ8aQtiWU6gvuMXQ0OwDLZikubKy
NUMuZC/nMf299/XhUHdCiOOsmn435ijBb+sLczIY1zK4oQn4EN5vLi+g5n9d87b+
MQ1PL+4kcMxHSyEY9i+yGYjf+iUipy6/ZXj7ZQIDAQABAoIBACpMjZSWM98/9lTr
FYFGHTTdSh/E0pCbUTbz7TT4gB/bfjRo6K2kEM8yL3XKEqh43jsr2lNb5wSMEITg
Ldp5dgDHNq2F9MAgpL5LHbG2rUXlQVn9/HTS0qUizvQt7Gup05HpmVmONBO9tsEg
8fXGLJ7J7MhOqisz8KH2ojN4amVWXu0m01ayAvrwHwmz06IJwJZ4fRHclf0Gl9h/
NjpJKpFlm+mToFPxRjQisYBDyTq0QwAZ6UShTG7wgWrKuJ6MrfH98DbfjTvqNHM0
XWVXdhTBdNwAK6erIBKABHz7p3/Z5iVd7g5Hdi2VfYiL/niSdMVEFtTu8h8suY4l
G40aiM0CgYEA3S82buU9IlUOyyIA5h7X4AILyQyoZIr3BETxpxP5m92C2E6RX+NV
ISQoh5zMAoCZ4YpZQrOYo2VhGXEq1zapiCdO6HZmgctS5nvExodRuQVu5rYeQ3P6
Nm1xBT3pbjpEPpQ8nNcx9ZFvsZ1XrspJ+q5Mwbaj5T8cOzbBCfoWmXMCgYEAxXVf
cMn3wkiBvMlwO01NlnMXfVIpciBQX3QkSzYe9oY06LdMbdLgiGv7/m6SI3RlaONt
pKecULrz6pyBveoRJk81FBeg8dkmngpiNMPQTLTS8OGeea83LdUl7zVjal+0GpRN
gP/HRW+9Jp6O5+4d6j89QoQLzGTPo7oef4zowccCgYBc76aOiBHc6CJ0JdB84L7S
J+ntyzzCKkXKbHGhQ1phLHz7CGA7CxlM+JVzDeYGsyR1SR1iUnYzSbi36P4YOaaY
R/P25zEBHn6xy5WN2XP0Kx1DIYirzQJ4dhnEGxSHNUJRjRW+zQj35ukolzUtg1/8
TdqAlo5dF9xz4PjRiVyPkwKBgBC/tvvDNe/V5KNV1t5A3V7wnkJ0EK3sjcS6/kUe
7xtsINrIiYQbSg5oUnSvflfhjKSL/gXkbb7vTLdO1TZ9vzynpVHx+yXojH0FVnUx
Ut7ey7HBAYdC1IRfuxsCRU+FlKpYgAZ8K7P5GWtIMcj8iq8O9CxLNRD+UBqMNAAP
vMKLAoGBAJ4R0UMAeTFMzBuFe089Tw8nk8qbSc52WGLoku0ZBZTvR4W7Bxpl2zWs
6luds7rbJXYI6XIyDMrRqrhsAxtGSWB1QTTLxhZNiFp8kD9E7bCj73+v4uT3e/eV
sLtvIQBTmlOHmeCiT2p0BMms3C/yUoANMk9ZmNOhloBru8VuOPGl
-----END RSA PRIVATE KEY-----""")
    )

    # 获取PR相关信息
    pr_url = event.data["pull_request"]["url"]
    repo_full_name = event.data["repository"]["full_name"]
    pr_number = event.data["pull_request"]["number"]
    
    # 创建评论
    comments_url = f"/repos/{repo_full_name}/issues/{pr_number}/comments"
    await gh.post(
        comments_url,
        data={
            "body": "感谢提交PR！我会尽快审核。"
        },
        oauth_token=installation_access_token["token"]
    )




if __name__ == "__main__":  # pragma: no cover
    app = web.Application()

    app.router.add_routes(routes)
    port = os.environ.get("PORT")
    if port is not None:
        port = int(port)
    else:
        port = 8080
    web.run_app(app, port=port)
