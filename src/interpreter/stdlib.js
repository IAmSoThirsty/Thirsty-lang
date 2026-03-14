const fs = require('fs');
const http = require('http');
const https = require('https');
const crypto = require('crypto');
const path = require('path');
const { WebSocketServer } = require('ws');

/**
 * Initialize and return standard library objects
 */
function initializeStandardLibrary() {
  const stdlib = {
    Math: {
      __builtin: true,
      PI: 3.14159265359,
      E: 2.71828182846,
      abs: (x) => Math.abs(x),
      sqrt: (x) => Math.sqrt(x),
      pow: (x, y) => Math.pow(x, y),
      floor: (x) => Math.floor(x),
      ceil: (x) => Math.ceil(x),
      round: (x) => Math.round(x),
      min: (...args) => Math.min(...args),
      max: (...args) => Math.max(...args),
      random: () => Math.random(),
      log: (x) => Math.log(x),
      log2: (x) => Math.log2(x)
    },

    String: {
      __builtin: true,
      toUpperCase: (str) => String(str).toUpperCase(),
      toLowerCase: (str) => String(str).toLowerCase(),
      trim: (str) => String(str).trim(),
      split: (str, separator) => String(str).split(separator),
      replace: (str, search, replacement) => String(str).replace(search, replacement),
      charAt: (str, index) => String(str).charAt(index),
      substring: (str, start, end) => String(str).substring(start, end),
      length: (str) => String(str).length,
      includes: (str, search) => String(str).includes(search)
    },

    Console: {
      __builtin: true,
      log: (...args) => console.log(...args),
      warn: (...args) => console.warn('\x1b[33m%s\x1b[0m', ...args),
      error: (...args) => console.error('\x1b[31m%s\x1b[0m', ...args),
      info: (...args) => console.info('\x1b[36m%s\x1b[0m', ...args),
      clear: () => console.clear(),
      table: (data) => console.table(data)
    },

    Process: {
      __builtin: true,
      args: process.argv,
      env: process.env,
      exit: (code = 0) => process.exit(code),
      cwd: () => process.cwd(),
      platform: process.platform,
      version: process.version,
      uptime: () => process.uptime()
    },

    Crypto: {
      __builtin: true,
      sha256: (data) => crypto.createHash('sha256').update(String(data)).digest('hex'),
      hmac: (key, data) => crypto.createHmac('sha256', key).update(String(data)).digest('hex'),
      uuid: () => crypto.randomUUID(),
      randomBytes: (size) => crypto.randomBytes(size).toString('hex')
    },

    Time: {
      __builtin: true,
      now: () => Date.now(),
      iso: () => new Date().toISOString(),
      format: (ts) => new Date(ts).toLocaleString(),
      sleep: (ms) => new Promise(resolve => setTimeout(resolve, ms))
    },

    File: {
      __builtin: true,
      read: (filePath) => fs.readFileSync(path.resolve(filePath), 'utf8'),
      write: (filePath, content) => {
        fs.writeFileSync(path.resolve(filePath), String(content), 'utf8');
        return true;
      },
      exists: (filePath) => fs.existsSync(path.resolve(filePath)),
      delete: (filePath) => {
        fs.unlinkSync(path.resolve(filePath));
        return true;
      },
      mkdir: (dirPath) => fs.mkdirSync(path.resolve(dirPath), { recursive: true }),
      rmdir: (dirPath) => fs.rmSync(path.resolve(dirPath), { recursive: true, force: true }),
      stats: (filePath) => {
        const s = fs.statSync(path.resolve(filePath));
        return {
          size: s.size,
          isDirectory: s.isDirectory(),
          isFile: s.isFile(),
          mode: s.mode,
          atime: s.atime,
          mtime: s.mtime,
          ctime: s.ctime,
          birthtime: s.birthtime
        };
      },
      watch: (targetPath, callback) => {
        return fs.watch(path.resolve(targetPath), { recursive: true }, (event, filename) => {
          if (typeof callback === 'function') callback(event, filename);
        });
      },
      list: (dirPath) => fs.readdirSync(path.resolve(dirPath))
    },

    Http: {
      __builtin: true,
      get: (url) => {
        return new Promise((resolve, reject) => {
          const protocol = url.startsWith('https') ? https : http;
          protocol.get(url, (res) => {
            let data = '';
            res.on('data', (chunk) => { data += chunk; });
            res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body: data }));
          }).on('error', (err) => reject(new Error(`HTTP GET failed: ${err.message}`)));
        });
      },
      post: (url, postData) => {
        return new Promise((resolve, reject) => {
          const urlObj = new URL(url);
          const protocol = urlObj.protocol === 'https:' ? https : http;
          const data = typeof postData === 'string' ? postData : JSON.stringify(postData);
          const options = {
            hostname: urlObj.hostname,
            port: urlObj.port,
            path: urlObj.pathname + urlObj.search,
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Content-Length': Buffer.byteLength(data)
            }
          };
          const req = protocol.request(options, (res) => {
            let responseData = '';
            res.on('data', (chunk) => { responseData += chunk; });
            res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body: responseData }));
          });
          req.on('error', (err) => reject(new Error(`HTTP POST failed: ${err.message}`)));
          req.write(data);
          req.end();
        });
      },
      createServer: (options = {}) => {
        const server = http.createServer();
        let wss = null;
        const ThirstyServer = {
          __builtin: true,
          onHandle: null,
          onWebSocket: null,
          listen: (port, callback) => {
            server.on('request', async (req, res) => {
              if (typeof ThirstyServer.onHandle === 'function') {
                let body = '';
                req.on('data', chunk => { body += chunk; });
                req.on('end', async () => {
                  const request = { method: req.method, url: req.url, headers: req.headers, body: body };
                  const response = await ThirstyServer.onHandle(request);
                  res.writeHead(response.status || 200, response.headers || { 'Content-Type': 'text/plain' });
                  res.end(typeof response.body === 'string' ? response.body : JSON.stringify(response.body));
                });
              } else {
                res.writeHead(200);
                res.end('Thirsty-Lang Sovereign Server Active');
              }
            });
            wss = new WebSocketServer({ server });
            wss.on('connection', (ws, req) => {
              if (typeof ThirstyServer.onWebSocket === 'function') {
                const client = {
                  send: (data) => ws.send(typeof data === 'string' ? data : JSON.stringify(data)),
                  onMessage: null,
                  onClose: null
                };
                ws.on('message', (msg) => {
                  if (typeof client.onMessage === 'function') client.onMessage(msg.toString());
                });
                ws.on('close', () => {
                  if (typeof client.onClose === 'function') client.onClose();
                });
                ThirstyServer.onWebSocket(client, { url: req.url, headers: req.headers });
              }
            });
            server.listen(port, callback);
          },
          stop: () => {
            if (wss) wss.close();
            server.close();
          }
        };
        return ThirstyServer;
      },
      _createFetch: (Http) => {
        return (url, options = {}) => {
          if (options.method === 'POST') return Http.post(url, options.body);
          return Http.get(url);
        };
      }
    },

    JSON: {
      __builtin: true,
      parse: (jsonString) => JSON.parse(jsonString),
      stringify: (value, replacer = null, space = 2) => JSON.stringify(value, replacer, space),
      isValid: (jsonString) => {
        try { JSON.parse(jsonString); return true; } catch { return false; }
      }
    }
  };

  return stdlib;
}

module.exports = { initializeStandardLibrary };

module.exports = { initializeStandardLibrary };
