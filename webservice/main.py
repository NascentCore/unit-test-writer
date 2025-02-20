import os
import base64
import json
import re
import time
import jwt
import requests
from github import Github
from flask import Flask, request, jsonify
from github import Auth
from dotenv import load_dotenv
# 从.env文件加载环境变量
load_dotenv()
app = Flask(__name__)
# GitHub App 配置信息
GITHUB_APP_ID = os.getenv("GITHUB_APP_ID")
GITHUB_PRIVATE_KEY = os.getenv("GITHUB_PRIVATE_KEY")
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")

# 用来获取 GitHub App 安装访问令牌
def get_installation_access_token(installation_id):
    now = int(time.time())
    payload = {
        "iat": now - 60,  # 即将到期的JWT的发放时间
        "exp": now + (10 * 60),  # JWT到期时间
        "iss": GITHUB_APP_ID,
    }
    # 使用私钥签名JWT
    jwt_token = jwt.encode(payload, GITHUB_PRIVATE_KEY, algorithm="RS256")
    # 获取访问令牌
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    headers = {"Authorization": f"Bearer {jwt_token}", "Accept": "application/vnd.github.v3+json"}
    response = requests.post(url, headers=headers)
    if response.status_code == 201:
        return response.json()["token"]
    else:
        raise Exception("Unable to get installation access token")

@app.route('/webhook', methods=['POST'])
def webhook():
    payload = request.get_data()
    event = request.headers.get('X-GitHub-Event')
    if event == 'push':
        push_data = json.loads(payload)
        # 获取仓库信息
        repo_name = push_data['repository']['full_name']
        installation_id = push_data['installation']['id']
        # 获取安装令牌
        installation_access_token = get_installation_access_token(installation_id)
        repo = Github(installation_access_token).get_repo(repo_name)
        if push_data['pusher']['name'] == 'unit-test-writer-1[bot]':
            return jsonify({"message": "Push event handled"}), 200
        check_and_generate_tests(repo, push_data)
        return jsonify({"message": "Push event handled"}), 200
    return jsonify({"message": "Event not handled"}), 200

def check_and_generate_tests(repo, push_data):
    # 获取推送的文件
    ref = push_data['ref']
    # 修改分支名获取逻辑，去掉 'refs/heads/' 前缀
    branch = ref.replace('refs/heads/', '')
    contents = repo.get_contents("", ref=branch)
    # 检查文件并提取没有单元测试的函数
    function_names = extract_functions_without_tests(contents)
    if not function_names:
        print("No functions need tests.")
        return
    # 生成单元测试代码
    test_code = generate_unit_tests(function_names)
    # 提交单元测试代码到一个新的文件
    create_pr_with_tests(repo, branch, test_code)
    
def extract_functions_without_tests(contents):
    function_names = []
    for content in contents:
        if content.type == 'file' and content.name.endswith('.py'):
            file_content = base64.b64decode(content.content).decode("utf-8")
            functions = re.findall(r'def (\w+)\(', file_content)
            for func in functions:
                if not is_tested(func, file_content):
                    function_names.append(func)
    return function_names

def is_tested(function_name, file_content):
    test_pattern = f'test_{function_name}'  # 假设测试函数名为 test_<函数名>
    if test_pattern in file_content:
        return True
    return False

def generate_unit_tests(function_names):
    test_code = """import unittest
class TestGenerated(unittest.TestCase):\n"""
    for func in function_names:
        test_code += f"""
    def test_{func}(self):
        # Test {func} function
        self.assertEqual({func}(), expected_output)  # Replace with actual test logic\n"""
    return test_code

def create_pr_with_tests(repo, branch, test_code):
    base_branch = 'main'  # 目标分支
    head_branch = branch  # 源分支
    # 获取目标分支和源分支的最新提交
    base_commit = repo.get_commit(base_branch)
    head_commit = repo.get_commit(head_branch)
    # 检查是否有差异
    if base_commit.sha == head_commit.sha:
        print(f"No changes between {base_branch} and {head_branch}, skipping PR creation.")
        return  # 如果没有差异，不创建 PR
    # 提交生成的单元测试文件
    test_file_path = 'tests/test_generated.py'
    try:
        contents = repo.get_contents(test_file_path, ref=head_branch)
        sha = contents.sha
    except:
        sha = None
    if sha:
        repo.update_file(test_file_path, "Updating unit tests", test_code, sha=sha, branch=head_branch)
    else:
        repo.create_file(test_file_path, "Adding unit tests", test_code, branch=head_branch)
    # 创建 PR
    pr_title = "Add unit tests for untested functions"
    pr_body = "This PR automatically adds unit tests for functions that lacked tests in the previous code."
    repo.create_pull(title=pr_title, body=pr_body, head=head_branch, base=base_branch)
    print("PR created with unit tests.")

if __name__ == '__main__':
    app.run(port=30004, host="0.0.0.0")