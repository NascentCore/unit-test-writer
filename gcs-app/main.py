import fnmatch
import os
from fastapi import FastAPI, HTTPException, Request
import hmac
import hashlib
import jwt
import time
from github import Github, Auth
import openai

# 从环境变量获取 GitHub App 相关配置
APP_ID = os.getenv("GITHUB_APP_ID")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
PRIVATE_KEY_PATH = "private-key.pem"  # 你的 GitHub App 私钥路径
LLM_API_KEY = os.getenv("DOUBAO_API_KEY")  # 使用豆包的 API KEY
LLM_API_BASE = "https://ark.cn-beijing.volces.com/api/v3/"
LLM_MODEL = "ep-20240721110948-mdv29"

# 设置豆包的 API 地址
openai.api_base = LLM_API_BASE
openai.api_key = LLM_API_KEY

# 读取私钥
with open(PRIVATE_KEY_PATH, "r") as f:
    PRIVATE_KEY = f.read()

app = FastAPI()

@app.get("/hello")
async def hello():
    return {"message": "hello world"}

@app.post("/webhook")
async def webhook_handler(request: Request):
    """处理 GitHub Webhook"""
    payload = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    if not signature or not verify_signature(payload, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    data = await request.json()
    event_type = request.headers.get("X-GitHub-Event")

    if event_type in ["push", "pull_request"]:
        repo_full_name = data["repository"]["full_name"]
        branch = data.get("ref", "").split("/")[-1]
        installation_id = data["installation"]["id"]  # 从 webhook 数据中获取

        # 触发代码分析
        analyze_repo(repo_full_name, branch, installation_id)  # 传入 installation_id

    return {"message": "Webhook received"}


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
    token = get_installation_token(installation_id)  # 使用传入的 installation_id
    g = Github(token)
    repo = g.get_repo(repo_full_name)
    
    contents = repo.get_contents("", ref=branch)
    python_files = []
    test_files = set()

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


def generate_test_code(file_content):
    """调用豆包大模型生成测试代码"""
    prompt = f"""
    你是一名 Python 开发者，熟悉 `pytest`，请为以下代码生成一个 `pytest` 风格的单元测试：
    {file_content}
    """
    response = openai.ChatCompletion.create(
        model=LLM_MODEL, 
        messages=[{"role": "system", "content": "你是一个专业的 Python 单元测试生成器。"},
                  {"role": "user", "content": prompt}]
    )
    return response["choices"][0]["message"]["content"]


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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 