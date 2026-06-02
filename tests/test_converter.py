"""Task 1.3: MarkItDownConverter 转换引擎封装测试。

测试目标：
- SUPPORTED 扩展名与 DropArea 一致（SSOT）
- convert(file_path) 返回 Markdown 字符串
- 文件不存在 → E_FILE_001
- 空文件 → E_FILE_002
- 超大文件 (>500MB) → E_FILE_003
- 0 字节/空文件 → 友好错误信息
- 密码保护 PDF / 损坏文件 → 转换错误（不抛 Python traceback）
- LLM api_key 可选：None 时不传
"""
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def converter(qapp):
    from src.core.converter import MarkItDownConverter

    return MarkItDownConverter()


def test_supported_set_matches_droparea():
    """SSOT：Converter.SUPPORTED 与 DropArea.SUPPORTED_EXTENSIONS 必须一致。"""
    from src.core.converter import MarkItDownConverter
    from src.ui.drop_area import SUPPORTED_EXTENSIONS
    assert MarkItDownConverter.SUPPORTED == SUPPORTED_EXTENSIONS


def test_converter_rejects_nonexistent_file(converter, tmp_path):
    """文件不存在 → E_FILE_001。"""
    from src.core.errors import ConversionError, ErrorCode

    fake = tmp_path / "does_not_exist.pdf"
    with pytest.raises(ConversionError) as exc:
        converter.convert(str(fake))
    assert exc.value.code == ErrorCode.E_FILE_001


def test_converter_rejects_empty_file(converter, tmp_path):
    """0 字节空文件 → E_FILE_002。"""
    from src.core.errors import ConversionError, ErrorCode

    empty = tmp_path / "empty.txt"
    empty.write_bytes(b"")
    with pytest.raises(ConversionError) as exc:
        converter.convert(str(empty))
    assert exc.value.code == ErrorCode.E_FILE_002


def test_converter_rejects_oversized_file(converter, tmp_path, monkeypatch):
    """超大文件 → E_FILE_003。"""
    from src.core.errors import ConversionError, ErrorCode

    # 不真造 500MB 文件：monkeypatch 报告大小
    fake = tmp_path / "big.pdf"
    fake.write_bytes(b"%PDF-1.4\n")
    # 用 os.path.getsize mock
    monkeypatch.setattr(
        "os.path.getsize",
        lambda p: 501 * 1024 * 1024 if "big" in p else 0
    )
    with pytest.raises(ConversionError) as exc:
        converter.convert(str(fake))
    assert exc.value.code == ErrorCode.E_FILE_003


def test_converter_calls_markitdown_with_correct_args(tmp_path, monkeypatch):
    """正常 PDF：传给 MarkItDown 的参数正确。"""
    from src.core.converter import MarkItDownConverter

    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")

    mock_result = MagicMock()
    mock_result.markdown = "# Hello\n\nWorld"
    mock_md = MagicMock()
    mock_md.convert.return_value = mock_result

    monkeypatch.setattr("src.core.converter.MarkItDown", lambda **kwargs: mock_md)
    monkeypatch.setattr("os.path.getsize", lambda p: 100)

    converter = MarkItDownConverter()
    result = converter.convert(str(pdf))
    assert result == "# Hello\n\nWorld"
    mock_md.convert.assert_called_once_with(str(pdf))


def test_converter_handles_markitdown_exception(tmp_path, monkeypatch):
    """MarkItDown 抛异常（如密码保护 PDF）→ ConversionError 不带 traceback。"""
    from src.core.converter import MarkItDownConverter
    from src.core.errors import ConversionError, ErrorCode

    pdf = tmp_path / "locked.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")

    mock_md = MagicMock()
    mock_md.convert.side_effect = Exception("PDF is password protected")
    monkeypatch.setattr("src.core.converter.MarkItDown", lambda **kwargs: mock_md)
    monkeypatch.setattr("os.path.getsize", lambda p: 100)

    converter = MarkItDownConverter()
    with pytest.raises(ConversionError) as exc:
        converter.convert(str(pdf))
    assert exc.value.code == ErrorCode.E_CONVERT_001


def test_converter_no_llm_api_key_param_v044(converter, tmp_path, monkeypatch):
    """v0.4.4+：LLM 图片描述已撤场，converter 不再接受 llm_api_key 参数。

    这个测试是 v0.4.3 之前 ``test_converter_passes_llm_api_key_when_provided``
    的替代：v0.4.4 移除参数后，调用 ``MarkItDownConverter(llm_api_key=...)``
    会 TypeError；反之 ``MarkItDownConverter()`` 正常工作。
    """
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    mock_md = MagicMock()
    mock_md.convert.return_value = MagicMock(markdown="# x")
    monkeypatch.setattr("src.core.converter.MarkItDown", lambda **kwargs: mock_md)
    monkeypatch.setattr("os.path.getsize", lambda p: 100)

    # 1. v0.4.4+ 无参构造 OK
    c = converter.__class__()
    md = c.convert(str(pdf))
    assert md == "# x"

    # 2. 传 llm_api_key= 必须 TypeError（参数已删）
    with pytest.raises(TypeError):
        converter.__class__(llm_api_key="sk-test")
