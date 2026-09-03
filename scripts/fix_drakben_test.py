import re
from pathlib import Path

def fix_test():
    p = Path('tests/test_adapter_drakben.py')
    content = p.read_text(encoding='utf-8')
    
    # Fix the denial test assertion
    content = content.replace("assert call_kwargs['success'] is False", "assert call_kwargs['content']['success'] is False")
    
    # Fix the authorized test assertion
    # The original was:
    # assert rec['tool'] == 'drakben'
    # assert rec['session_id'] == 'sess-test'
    # We want:
    # assert rec['source'] == 'drakben'
    # assert rec['session_id'] == 'sess-test'
    # assert rec['content']['success'] is True
    
    content = content.replace("assert rec['tool'] == 'drakben'", "assert rec['source'] == 'drakben'")
    
    # And we need to add the assert rec['content']['success'] is True
    # Let's look for where the existing ones are
    idx = content.find("assert rec['session_id'] == 'sess-test'")
    if idx != -1:
        # find end of that line
        end_idx = content.find('\n', idx)
        content = content[:end_idx+1] + "    assert rec['content']['success'] is True\n" + content[end_idx+1:]

    # Fix the target host test
    content = content.replace("assert 'No target host' in result.error", "assert 'Policy denied' in result.error")

    # Fix the target host test because it's not just 'No target host' anymore
    # Actually the error was "Policy denied: Action 'scan' denied: no target id supplied"
    # Let's just use a simpler assertion.
    content = content.replace("assert 'No target host' in result.error", "assert 'no target id supplied' in result.error")

    p.write_text(content, encoding='utf-8')
    print("Fixed tests")

if __name__ == "__main__":
    fix_test()
