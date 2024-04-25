from step_in_line.tf import remove_decorators


def test_remove_decorators_with_decorator():
    code = '    @step\n    def preprocess(arg1: str) -> str:\n        return "hello"'
    expected = 'def preprocess(arg1: str) -> str:\n    return "hello"'
    assert remove_decorators(code) == expected


def test_remove_decorators_without_decorator():
    code = 'def preprocess(arg1: str) -> str:\n    return "hello"'
    expected = 'def preprocess(arg1: str) -> str:\n    return "hello"'
    assert remove_decorators(code) == expected
