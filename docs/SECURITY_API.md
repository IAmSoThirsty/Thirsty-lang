# Thirsty-Lang Security API & Hardening

This document outlines the security primitives and hardening measures implemented in the Thirsty-Lang interpreter to ensure a secure, isolated execution environment.

## Security Primitives

Thirsty-Lang includes several built-in keywords for managing runtime security:

### `shield [name] { ... }`

Creates a protected execution context. All exceptions within the block are caught and handled, and the context is logged for telemetry.

### `armor [variable]`

Marks a variable as read-only (armored). Any subsequent attempt to reassign the variable will throw a `SecurityError`.

### `sanitize [variable]`

Performs in-place sanitization of a string variable, removing dangerous HTML tags, `script` blocks, and `javascript:` URIs.

### `morph on: ["strategy", ...]`

Enables specified code transformation strategies. Supported strategies include `injection`, `overflow`, `rename`, and `obfuscate`.

### `detect [target] { ... }`

Enables real-time threat detection for a specific target (variable, function, or module) within the following block.

### `defend with: [level]`

Sets the global defense level. Supported levels: `low`, `moderate`, `high`, `extreme`.

## Hardening Measures

The following internal measures prevent sandbox escapes and prototype pollution:

### 1. Environment Isolation

The `Environment` class uses `Object.create(null)` for its internal storage, preventing prototype pollution attacks that attempt to overwrite standard object properties.

### 2. Member Access Blocklist

Any attempt to access or assign to sensitive JavaScript properties via member indexing or dot notation is blocked. The blocklist includes:

- `constructor`
- `__proto__`
- `prototype`
- `call`
- `apply`
- `bind`

### 3. Enterprise Telemetry

The interpreter includes a structured JSON logger that records all security violations, shielded context transitions, and defense level changes.

```json
{
  "timestamp": "2026-02-24T15:46:35.219Z",
  "level": "SECURITY",
  "component": "THIRSTY_RUNTIME",
  "message": "Illegal property access attempt",
  "data": { "property": "constructor" }
}
```

## Policy Integration

Thirsty-Lang is designed to integrate with the **T.A.R.L.** (Threat Analysis & Risk Leveling) bridge for advanced AI-driven security policies. When available, the `SecurityManager` will delegate strategy enforcement and threat monitoring to the TARL engine.
