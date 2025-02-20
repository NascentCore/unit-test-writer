import fnmatch
import os
from fastapi import FastAPI, HTTPException, Request
import hmac
import hashlib
import jwt
import time
from github import Github, Auth
import openai
from typing import Dict

# 从环境变量获取 GitHub App 相关配置
APP_ID = os.getenv("GITHUB_APP_ID")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
# PRIVATE_KEY_PATH = "private-key.pem"  # 你的 GitHub App 私钥路径
# LLM_API_KEY = os.getenv("DOUBAO_API_KEY")  # 使用豆包的 API KEY
LLM_API_KEY = "ff9ed2dd-cdf0-40d4-b4ec-d3aa19e2bd0b"  # 使用豆包的 API KEY
LLM_API_BASE = "https://ark.cn-beijing.volces.com/api/v3/"
LLM_MODEL = "ep-20240721110948-mdv29"

PRIVATE_KEY= """-----BEGIN RSA PRIVATE KEY-----
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
-----END RSA PRIVATE KEY-----"""

# 设置豆包的 API 地址
openai.api_base = LLM_API_BASE
openai.api_key = LLM_API_KEY

# # 读取私钥
# with open(PRIVATE_KEY_PATH, "r") as f:
#     PRIVATE_KEY = f.read()

# app = FastAPI()

# @app.get("/hello")
# async def hello():
#     return {"message": "hello world"}

# @app.post("/webhook")
# async def webhook_handler(request: Request):
#     """处理 GitHub Webhook"""
#     payload = await request.body()
#     signature = request.headers.get("X-Hub-Signature-256")

#     if not signature or not verify_signature(payload, signature):
#         raise HTTPException(status_code=401, detail="Invalid signature")

#     data = await request.json()
#     event_type = request.headers.get("X-GitHub-Event")

#     if event_type in ["push", "pull_request"]:
#         repo_full_name = data["repository"]["full_name"]
#         branch = data.get("ref", "").split("/")[-1]
#         installation_id = data["installation"]["id"]  # 从 webhook 数据中获取

#         # 触发代码分析
#         analyze_repo(repo_full_name, branch, installation_id)  # 传入 installation_id

#     return {"message": "Webhook received"}


# 生成 GitHub API 访问 Token
def get_installation_token(installation_id):
    jwt_token = generate_jwt()
    g = Github(jwt_token)
    installation = g.get_installation(installation_id)
    return g.get_app_installation_access_token(installation.id).token


def verify_signature(payload: bytes, signature: str):
    """校验 GitHub Webhook 的 HMAC-SHA256 签名"""
    mac = hmac.new(WEBHOOK_SECRET.encode(), msg=payload, digestmod=hashlib.sha256)
    expected_signature = f"sha256={mac.hexdigest()}"
    return hmac.compare_digest(expected_signature, signature)

def generate_jwt():
    """使用 GitHub App 的私钥生成 JWT"""
    payload = {
        "iat": int(time.time()),
        "exp": int(time.time()) + (10 * 60),  # 10分钟有效期
        "iss": APP_ID,
    }
    return jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")

def analyze_repo(repo_full_name, branch, installation_id):
    """分析仓库中的 Python 文件，找出缺少测试的文件"""
    print("test0")
    token = get_installation_token(installation_id)  # 使用传入的 installation_id
    print("test1")
    g = Github(token)
    repo = g.get_repo(repo_full_name)
    print("test2")
    contents = repo.get_contents("", ref=branch)
    python_files = []
    test_files = set()
    print("test3")

    while contents:
        file_content = contents.pop(0)
        if file_content.type == "dir":
            contents.extend(repo.get_contents(file_content.path, ref=branch))
        elif fnmatch.fnmatch(file_content.path, "*.py"):
            python_files.append(file_content.path)
            if "test" in file_content.path or file_content.path.startswith("tests/"):
                test_files.add(file_content.path)

    # 找出没有对应测试的文件
    missing_tests = [
        f for f in python_files if f"test_{f}" not in test_files and f"tests/{f}" not in test_files
    ]

    for file in missing_tests:
        generate_test_file(repo, file, branch)

def generate_test_file(repo, file_path, branch):
    """为缺少测试的 Python 文件创建测试文件"""
    content = repo.get_contents(file_path, ref=branch).decoded_content.decode()
    test_code = generate_test_code(content)

    test_filename = f"tests/test_{os.path.basename(file_path)}"
    try:
        existing_file = repo.get_contents(test_filename, ref=branch)
        repo.update_file(test_filename, "Update test file", test_code, existing_file.sha, branch=branch)
    except:
        repo.create_file(test_filename, "Add test file", test_code, branch=branch)

    print(f"Added test file: {test_filename}")

def generate_test_code(file_content: str) -> str:
    """调用豆包大模型生成测试代码"""
    # 配置OpenAI客户端
    client = openai.OpenAI(
        base_url=LLM_API_BASE,
        api_key=LLM_API_KEY
    )
    
    prompt = f"""
    你是一名 Python 开发者，熟悉 `pytest`，请为以下代码生成一个 `pytest` 风格的单元测试：
    {file_content}

    要求：
    1. 你的输出仅包含测试代码，不要包含任何解释或说明
    2. 你的输出使用plain text格式, 不要包含任何markdown格式
    2. 测试代码需要覆盖所有可能的输入和输出情况
    """
    
    # 调用API生成测试代码
    completion = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": "你是一个专业的 Python 单元测试生成器。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        timeout=60  # 60秒超时
    )
    
    # 确保返回完整的响应文本
    response_text = completion.choices[0].message.content

    # 如果返回的文本以```python开头，则去掉```python和结尾的``` 
    if response_text.startswith("```python"):
        response_text = response_text[len("```python"):].strip("```")

    return response_text
