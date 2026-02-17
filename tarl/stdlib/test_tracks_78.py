"""
Thirsty-Lang Tracks 7-8 Tests
Test suite for IDE Extensions and Playground modules
"""

import sys
import os

# Add modules to path
test_dir = os.path.dirname(__file__)
sys.path.insert(0, test_dir)

from tarl_playground import (
    CodeExecutor,
    REPLSession,
    SessionManager,
    CodeSharingService,
    WebREPL
)


def test_code_executor():
    """Test code executor"""
    print("Testing Code Executor...")
    
    executor = CodeExecutor()
    
    # Execute simple code
    result = executor.execute('x = 10\nprint(x)')
    assert result['success'] is True
    assert 'print' in result['stdout'] or '10' in result['stdout']
    
    # Execute code with error
    result = executor.execute('print(undefined_var)')
    assert result['success'] is False
    assert 'NameError' in result['error']
    
    # Execute code with syntax error
    result = executor.execute('if True\nprint("missing colon")')
    assert result['success'] is False
    assert 'SyntaxError' in result['error']
    
    print("✓ Code Executor tests passed")


def test_repl_session():
    """Test REPL session"""
    print("Testing REPL Session...")
    
    session = REPLSession('test-session')
    
    # Execute code
    result = session.execute('x = 42')
    assert result['success'] is True
    
    # Variables should persist
    result = session.execute('print(x)')
    assert result['success'] is True
    
    # Check history
    history = session.get_history()
    assert len(history) == 2
    assert history[0]['code'] == 'x = 42'
    
    # Reset session
    session.reset()
    assert len(session.get_history()) == 0
    
    print("✓ REPL Session tests passed")


def test_session_manager():
    """Test session manager"""
    print("Testing Session Manager...")
    
    manager = SessionManager()
    
    # Create session
    session_id = manager.create_session()
    assert session_id is not None
    assert len(session_id) == 16
    
    # Get session
    session = manager.get_session(session_id)
    assert session is not None
    assert session.session_id == session_id
    
    # Delete session
    manager.delete_session(session_id)
    assert manager.get_session(session_id) is None
    
    print("✓ Session Manager tests passed")


def test_code_sharing():
    """Test code sharing service"""
    print("Testing Code Sharing...")
    
    service = CodeSharingService()
    
    # Create snippet
    snippet_id = service.create_snippet(
        'print("Hello")',
        title='Greeting',
        author='TestUser'
    )
    assert snippet_id is not None
    
    # Get snippet
    snippet = service.get_snippet(snippet_id)
    assert snippet is not None
    assert snippet.code == 'print("Hello")'
    assert snippet.title == 'Greeting'
    
    # List snippets
    snippets = service.list_snippets()
    assert len(snippets) >= 1
    assert snippets[0]['id'] == snippet_id
    
    print("✓ Code Sharing tests passed")


def test_web_repl():
    """Test web REPL"""
    print("Testing Web REPL...")
    
    repl = WebREPL()
    
    # Create session
    response = repl.handle_create_session()
    assert 'session_id' in response
    session_id = response['session_id']
    
    # Execute code
    result = repl.handle_execute(session_id, 'x = 100\nprint(x)')
    assert result['success'] is True
    
    # Share code
    response = repl.handle_share_code('print("Shared")', title='Test')
    assert 'snippet_id' in response
    assert 'url' in response
    
    # Get snippet
    snippet = repl.handle_get_snippet(response['snippet_id'])
    assert snippet['code'] == 'print("Shared")'
    
    print("✓ Web REPL tests passed")


def test_ide_extensions():
    """Test IDE extension files exist"""
    print("Testing IDE Extensions...")
    
    # Navigate up from stdlib to Thirsty-Lang root
    stdlib_dir = os.path.dirname(test_dir)
    thirsty_lang_root = os.path.dirname(stdlib_dir)
    
    # Check VS Code extension
    vscode_dir = os.path.join(thirsty_lang_root, 'ide-extensions', 'vscode')
    assert os.path.exists(os.path.join(vscode_dir, 'package.json')), \
        f"VS Code package.json not found at {vscode_dir}"
    assert os.path.exists(os.path.join(vscode_dir, 'syntaxes', 'thirsty.tmLanguage.json')), \
        "VS Code syntax file not found"
    
    # Check Vim syntax
    vim_dir = os.path.join(thirsty_lang_root, 'ide-extensions', 'vim')
    assert os.path.exists(os.path.join(vim_dir, 'syntax', 'thirsty.vim')), \
        "Vim syntax file not found"
    
    # Check Emacs mode
    emacs_dir = os.path.join(thirsty_lang_root, 'ide-extensions', 'emacs')
    assert os.path.exists(os.path.join(emacs_dir, 'thirsty-mode.el')), \
        "Emacs mode file not found"
    
    print("✓ IDE Extension files exist")


def run_all_tests():
    """Run all Track 7-8 tests"""
    print("\n" + "="*50)
    print("THIRSTY-LANG TRACKS 7-8 TEST SUITE")
    print("IDE Extensions, Playground")
    print("="*50 + "\n")
    
    try:
        test_code_executor()
        test_repl_session()
        test_session_manager()
        test_code_sharing()
        test_web_repl()
        test_ide_extensions()
        
        print("\n" + "="*50)
        print("✓ ALL TRACKS 7-8 TESTS PASSED")
        print("="*50)
        return True
    
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
