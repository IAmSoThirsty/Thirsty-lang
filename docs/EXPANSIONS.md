<!--                                         [2026-03-03 13:45] -->
<!--                                        Productivity: Active -->
# Universal Thirsty Family (UTF) — Architecture

The **Universal Thirsty Family** is the definitive 6-tier language architecture of Thirsty-lang. Each tier is a superset of all previous tiers and cannot be decoupled from the system.

## Tier Overview

| Tier | Name | Description | File Extension |
|------|------|-------------|----------------|
| 1 | **Thirsty-Lang** | Core language — variables, control flow, security primitives | `.thirsty` |
| 2 | **Thirst of Gods** | OOP, async/await, advanced data structures | `.thirstofgods` |
| 3 | **T.A.R.L.** | Defensive policy VM | — |
| 4 | **Shadow Thirsty** | Dual-plane verified compiler | — |
| 5 | **TSCG** | Symbolic compression engine | — |
| 6 | **TSCG-B** | Binary encoding layer | — |

---

## Tier 1 — Thirsty-Lang

The foundation. All other tiers build on Tier 1.

**Features:**
- Variable declaration (`drink`)
- Output (`pour`)
- Input (`sip`)
- Comments (`//`)
- Conditionals (`thirsty` / `hydrated`)
- Loops (`refill`)
- Functions (`glass`)
- Arrays (`reservoir`)
- Classes (`fountain`)
- Standard Library (Math, String)
- T.A.R.L. security primitives (`shield`, `armored`)

**Use when:** Running standard `.thirsty` programs.

---

## Tier 2 — Thirst of Gods

Extends Tier 1 with advanced object-oriented and async capabilities.

**Additional Features:**
- `fountain ClassName extends BaseClass` — class inheritance
- `cascade funcName(params)` — async function declaration
- `await expr` — async expression (runs synchronously in sync contexts)
- `import Name from "path"` — module imports
- `export varName` — module exports
- `floodmap()` — create a map (plain object)
- `poolset()` — create a set (array)
- `spring interface Name { }` — interface declaration

**File extension:** `.thirstofgods`

---

## Tier 3 — T.A.R.L. (Thirsty's Active Resistance Language)

A JavaScript policy VM that evaluates security policies against execution contexts.

**Built-in Policies:**
- `input-sanitization` — blocks dangerous inputs (`<script>`, `eval()`, `__proto__`, etc.)
- `rate-limiting` — enforces request rate limits per key/window
- `access-control` — role-based access control (admin/user/guest)

**API:**
```javascript
const { TARL } = require('./src/utf/components/tarl');
const tarl = new TARL();
const result = await tarl.evaluate({ input: 'safe', role: 'user', resource: 'file', action: 'read' });
// → { verdict: 'ALLOW', results: [...] }
```

Custom policies can be added with `tarl.addPolicy(name, fn)`.

---

## Tier 4 — Shadow Thirsty

A dual-plane compiler that produces two independent representations of any Thirsty-lang source. Execution is only permitted if both planes agree (tamper detection).

**Planes:**
- **Plane A (Surface):** Tokenized representation with SHA-256 checksum
- **Plane B (Shadow):** HMAC-signed, per-token hashed representation

**API:**
```javascript
const { ShadowThirsty } = require('./src/utf/components/shadow-thirsty');
const shadow = new ShadowThirsty();
const compiled = shadow.compile(sourceCode);
const result = shadow.verify(compiled); // { valid: true, checksum: '...' }
shadow.execute(compiled);               // throws if tampered
```

---

## Tier 5 — TSCG (Thirsty's Symbolic Compression Grammar)

A symbol table-based source compressor that maps recurring tokens to short `§<id>` symbols.

**API:**
```javascript
const { TSCG } = require('./src/utf/components/tscg');
const tscg = new TSCG();
const result = tscg.compress(sourceCode);
// → { compressed, originalLength, compressedLength, ratio, symbolCount }
const restored = tscg.decompress(result.compressed);
```

---

## Tier 6 — TSCG-B (Binary Encoding)

Encodes TSCG-compressed output into a binary format with a magic header (`0x54534347` = `TSCG`), version field, and length-prefixed content.

**Format:** `magic(4) + version(2) + flags(2) + contentLength(4) + content`

**API:**
```javascript
const { TSCGB } = require('./src/utf/components/tscg-b');
const tscgb = new TSCGB();
const binary = tscgb.encode(compressedString); // → Buffer
const decoded = tscgb.decode(binary);           // → string
tscgb.encodeToFile(compressedString, path);
const content = tscgb.decodeFromFile(path);
```

---

## UTF Registry

The `UTFRegistry` class provides a unified factory for all 6 tiers:

```javascript
const { UTFRegistry } = require('./src/utf');
const registry = new UTFRegistry();

const t1 = registry.create(1);                  // ThirstyLang
const t2 = registry.create('thirst-of-gods');   // ThirstOfGods
const t3 = registry.create('tarl');             // TARL
const t4 = registry.create('shadow-thirsty');   // ShadowThirsty
const t5 = registry.create('tscg');             // TSCG
const t6 = registry.create('tscg-b');           // TSCGB
```

---

## UTF CLI

```bash
node src/utf/cli.js [options] [file]

Options:
  --tier <name>   Select UTF tier
  --compress      TSCG compress a file
  --verify        Shadow Thirsty verify a file
  --help          Show help
```

---

See `examples/utf/` for working examples of all 6 tiers.
