from repo import analyze_repo

def main():
    repo_full_name = "NascentCore/my-unittest"
    branch = "main"
    installation_id = 42830669  # GitHub App 的 installation ID
    
    try:
        analyze_repo(repo_full_name, branch, installation_id)
        print(f"成功为 {repo_full_name} 生成测试文件")
    except Exception as e:
        print(f"生成测试文件时发生错误: {str(e)}")

if __name__ == "__main__":
    main()