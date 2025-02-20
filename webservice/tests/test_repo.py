import pytest
from unittest.mock import Mock, patch
from webservice.repo import generate_test_file, generate_test_code

FILE_PATH = "test_cache/repo/lib.py"

def test_generate_test_file():
    """测试生成测试文件的基本功能"""
    # 准备测试数据
    mock_repo = Mock()
    mock_file_content = Mock()
    
    # 模拟源文件内容
    source_code = """
def add(a: int, b: int) -> int:
    return a + b
    """
    mock_file_content.decoded_content = source_code.encode()
    
    # 模拟GitHub API调用
    mock_repo.get_contents.side_effect = [
        mock_file_content,  # 返回源文件内容
        Exception()  # 模拟测试文件不存在的情况
    ]
    
    # 模拟生成的测试代码
    expected_test_code = """
def test_add():
    assert add(1, 2) == 3
    """
    
    # 模拟generate_test_code的返回值
    with patch('webservice.repo.generate_test_code', return_value=expected_test_code):
        # 执行测试
        generate_test_file(mock_repo, "my-unittest/example.py", "main")
    
    # 验证get_contents的调用
    assert mock_repo.get_contents.call_count == 2
    mock_repo.get_contents.assert_any_call("my-unittest/example.py", ref="main")
    mock_repo.get_contents.assert_any_call("tests/test_example.py", ref="main")
    
    # 验证create_file的调用
    mock_repo.create_file.assert_called_once_with(
        "tests/test_example.py",
        "Add test file",
        expected_test_code,
        branch="main"
    )

def test_generate_test_file_update_existing():
    """测试更新已存在的测试文件的场景"""
    # 准备测试数据
    mock_repo = Mock()
    mock_file_content = Mock()
    mock_existing_test = Mock()
    
    # 模拟源文件内容
    source_code = """
def add(a: int, b: int) -> int:
    return a + b
    """
    mock_file_content.decoded_content = source_code.encode()
    
    # 模拟已存在的测试文件
    mock_existing_test.sha = "existing_file_sha"
    
    # 模拟GitHub API调用
    mock_repo.get_contents.side_effect = [
        mock_file_content,  # 返回源文件内容
        mock_existing_test  # 返回已存在的测试文件
    ]
    
    # 模拟生成的测试代码
    expected_test_code = """
def test_add():
    assert add(1, 2) == 3
    """
    
    # 模拟generate_test_code的返回值
    with patch('webservice.repo.generate_test_code', return_value=expected_test_code):
        # 执行测试
        generate_test_file(mock_repo, "my-unittest/example.py", "main")
    
    # 验证update_file的调用
    mock_repo.update_file.assert_called_once_with(
        "tests/test_example.py",
        "Update test file",
        expected_test_code,
        mock_existing_test.sha,
        branch="main"
    )

def test_generate_test_code():
    """测试生成测试代码的基本功能"""
    # 准备测试数据
    file_content = "def add_function(a, b):\n    return a + b"
    
    # 执行测试
    test_code = generate_test_code(file_content)

    print(test_code)
    
    # 验证生成的测试代码
    assert isinstance(test_code, str)  # 验证生成的测试代码是字符串


