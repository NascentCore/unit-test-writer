import pytest
from unittest.mock import Mock, patch
from main import generate_test_file

def test_generate_test_file_create_new():
    """测试创建新的测试文件的场景"""
    # 模拟数据
    mock_repo = Mock()
    mock_file_content = Mock()
    mock_file_content.decoded_content = b"def sample_function():\n    return True"
    
    # 模拟 get_contents 在获取源文件时的返回值
    mock_repo.get_contents.side_effect = [
        mock_file_content,  # 第一次调用返回源文件内容
        Exception()  # 第二次调用模拟测试文件不存在的情况
    ]
    
    file_path = "sample/path/example.py"
    branch = "main"
    
    # 模拟 generate_test_code 的返回值
    test_code = """
def test_sample_function():
    assert sample_function() is True
"""
    
    with patch('main.generate_test_code', return_value=test_code):
        generate_test_file(mock_repo, file_path, branch)
    
    # 验证调用
    assert mock_repo.get_contents.call_count == 2
    mock_repo.get_contents.assert_any_call(file_path, ref=branch)
    mock_repo.get_contents.assert_any_call("tests/test_example.py", ref=branch)
    
    # 验证创建新文件的调用
    mock_repo.create_file.assert_called_once_with(
        "tests/test_example.py",
        "Add test file",
        test_code,
        branch=branch
    )

def test_generate_test_file_update_existing():
    """测试更新已存在的测试文件的场景"""
    # 模拟数据
    mock_repo = Mock()
    mock_file_content = Mock()
    mock_file_content.decoded_content = b"def sample_function():\n    return True"
    
    mock_existing_test = Mock()
    mock_existing_test.sha = "existing_file_sha"
    
    # 模拟 get_contents 的返回值
    mock_repo.get_contents.side_effect = [
        mock_file_content,  # 源文件内容
        mock_existing_test  # 已存在的测试文件
    ]
    
    file_path = "sample/path/example.py"
    branch = "main"
    
    # 模拟 generate_test_code 的返回值
    test_code = """
def test_sample_function():
    assert sample_function() is True
"""
    
    with patch('main.generate_test_code', return_value=test_code):
        generate_test_file(mock_repo, file_path, branch)
    
    # 验证调用
    assert mock_repo.get_contents.call_count == 2
    mock_repo.get_contents.assert_any_call(file_path, ref=branch)
    mock_repo.get_contents.assert_any_call("tests/test_example.py", ref=branch)
    
    # 验证更新文件的调用
    mock_repo.update_file.assert_called_once_with(
        "tests/test_example.py",
        "Update test file",
        test_code,
        mock_existing_test.sha,
        branch=branch
    )

def test_generate_test_file_error_handling():
    """测试源文件不存在的错误处理场景"""
    mock_repo = Mock()
    
    # 模拟源文件不存在的情况
    mock_repo.get_contents.side_effect = Exception("File not found")
    
    file_path = "sample/path/nonexistent.py"
    branch = "main"
    
    with pytest.raises(Exception):
        generate_test_file(mock_repo, file_path, branch) 