# Thirsty-Lang Standard Library

**Complete standard library implementation for the Thirsty-Lang programming language.**

## Overview

The Thirsty-Lang standard library provides 17 production-ready modules across 8 tracks:

- **Track 1**: Core data structures & utilities
- **Track 2**: Networking & HTTP
- **Track 3**: File I/O operations  
- **Track 4**: Database support
- **Track 5**: Package management
- **Track 6**: Language Server Protocol
- **Track 7**: IDE extensions
- **Track 8**: Mobile playground

**Stats**: 17 modules • ~3,900 lines of code • 36 passing tests

---

## Installation

```bash
# Clone the repository
git clone https://github.com/IAmSoThirsty/Thirsty-Lang.git
cd Thirsty-Lang

# Run tests
cd tarl/stdlib
python test_stdlib.py        # Core modules
python test_network.py        # Network & HTTP
python test_fileio.py         # File I/O
python test_tracks_456.py     # Database, Registry, LSP
python test_tracks_78.py      # IDE Extensions, Playground
```

---

## Module Reference

### Track 1: Core Modules

**Collections** (`tarl_collections.py`)

```python
from tarl.stdlib import Deque, OrderedDict, Counter, Heap

# Deque
dq = Deque()
dq.append(1)
dq.appendleft(0)

# Counter
counter = Counter([1, 2, 2, 3, 3, 3])
counter.most_common(1)  # [(3, 3)]
```

**Itertools** (`tarl_itertools.py`)

```python
from tarl.stdlib import Itertools

# Functional operations
numbers = [1, 2, 3, 4]
squared = Itertools.map(lambda x: x**2, numbers)
evens = Itertools.filter(lambda x: x % 2 == 0, numbers)
```

**DateTime** (`tarl_datetime.py`)

```python
from tarl.stdlib import DateTime, TimeDelta

now = DateTime.now()
tomorrow = now + TimeDelta(days=1)
print(tomorrow.format('%Y-%m-%d'))
```

**Math** (`tarl_math.py`)

```python
from tarl.stdlib import Math

Math.mean([1, 2, 3, 4, 5])     # 3.0
Math.stdev([1, 2, 3, 4, 5])    # 1.41...
Math.gcd(48, 18)               # 6
```

### Track 2: Network & HTTP

**HTTP Client** (`tarl_http_client.py`)

```python
from tarl.stdlib import HttpClient

client = HttpClient(base_url='https://api.example.com')
response = client.get('/users')
users = response.json()
```

**HTTP Server** (`tarl_http_server.py`)

```python
from tarl.stdlib import HttpServer, TarlResponse

server = HttpServer(port=8000)

@server.get('/hello')
def hello(request):
    return TarlResponse.text('Hello, World!')

server.listen()
```

**WebSocket** (`tarl_websocket.py`)

```python
from tarl.stdlib import WebSocketClient

ws = WebSocketClient('ws://localhost:8080')
ws.connect()
ws.send('Hello!')
message = ws.receive()
ws.close()
```

### Track 3: File I/O

**Path** (`tarl_path.py`)

```python
from tarl.stdlib import Path

p = Path.cwd() / 'data' / 'file.txt'
print(p.name, p.suffix, p.parent)

for json_file in p.parent.glob('*.json'):
    print(json_file)
```

**Filesystem** (`tarl_filesystem.py`)

```python
from tarl.stdlib import File, Directory

# File operations
File.write_json('config.json', {'api_key': 'secret'})
config = File.read_json('config.json')

# Directory operations
files = Directory.list_files('/path/to/dir', recursive=True)
```

**Archives** (`tarl_archives.py`)

```python
from tarl.stdlib import ZipArchive, Archive

# Create archive
ZipArchive.create('backup.zip', ['file1.txt', 'file2.txt'])

# Auto-detect and extract
Archive.extract('archive.tar.gz', 'output/')
```

### Track 4: Database

**SQLite** (`tarl_db_sqlite.py`)

```python
from tarl.stdlib import SQLiteDatabase

db = SQLiteDatabase('app.db')
db.create_table('users', 'id INTEGER PRIMARY KEY, name TEXT')
db.insert('users', {'name': 'Alice'})
users = db.select('users', where='name LIKE "A%"')
```

### Track 5: Package Registry

**Package Management** (`tarl_package.py`)

```python
from tarl.stdlib import Registry, DependencyResolver, PackageVersion

# Check version compatibility
v = PackageVersion.parse('1.2.3')
v.satisfies('~1.2.0')  # True (>=1.2.0 <1.3.0)
v.satisfies('^1.0.0')  # True (>=1.0.0 <2.0.0)

# Resolve dependencies
registry = Registry()
resolver = DependencyResolver(registry)
packages = resolver.resolve('myapp')
```

### Track 6: Language Server Protocol

**LSP Server** (`tarl_lsp.py`)

```python
from tarl.stdlib import LSPServer

lsp = LSPServer()
lsp.initialize({'processId': 1234})

# Get diagnostics
diagnostics = lsp.open_document('file:///code.tarl', code)

# Get completions
completions = lsp.get_completions('file:///code.tarl', {'line': 5, 'character': 10})
```

### Track 8: Playground

**Web REPL** (`tarl_playground.py`)

```python
from tarl.stdlib import WebREPL

repl = WebREPL()

# Create session
session = repl.handle_create_session()

# Execute code
result = repl.handle_execute(session['session_id'], 'print("Hello")')

# Share code
snippet = repl.handle_share_code('print("Shared")', title='Example')
```

---

## IDE Support (Track 7)

### VS Code Extension

```bash
cd ide-extensions/vscode
npm install
npm run compile
code --install-extension .
```

### Vim/Neovim

```bash
mkdir -p ~/.vim/syntax
cp ide-extensions/vim/syntax/thirsty.vim ~/.vim/syntax/
echo "au BufRead,BufNewFile *.tarl set filetype=thirsty" >> ~/.vimrc
```

### Emacs

```elisp
;; Add to ~/.emacs or ~/.emacs.d/init.el
(add-to-list 'load-path "/path/to/ide-extensions/emacs")
(require 'thirsty-mode)
```

---

## Running the Playground

```bash
cd playground/web
python -m http.server 8080
# Visit http://localhost:8080
```

---

## Testing

Run all tests:

```bash
cd tarl/stdlib
python -m pytest  # If pytest installed

# Or run individually:
python test_stdlib.py
python test_network.py
python test_fileio.py
python test_tracks_456.py
python test_tracks_78.py
```

**Test Coverage**: 36/36 tests passing (100%)

---

## License

MIT License - See LICENSE file for details

---

## Contributing

Contributions welcome! Please submit pull requests to the main repository.

**Repository**: <https://github.com/IAmSoThirsty/Thirsty-Lang>
