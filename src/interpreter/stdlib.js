/**
 * Standard Library Module
 * Provides built-in Math, String, File, and Http utilities
 */

const fs = require('fs');
const http = require('http');
const https = require('https');

/**
 * Initialize and return standard library objects
 * @returns {Object} Object containing Math, String, File, and Http utilities
 */
function initializeStandardLibrary() {
  return {
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
      random: () => Math.random()
    },

    String: {
      __builtin: true,
      toUpperCase: (str) => String(str).toUpperCase(),
      toLowerCase: (str) => String(str).toLowerCase(),
      trim: (str) => String(str).trim(),
      split: (str, separator) => String(str).split(separator),
      replace: (str, search, replacement) => String(str).replace(search, replacement),
      charAt: (str, index) => String(str).charAt(index),
      substring: (str, start, end) => String(str).substring(start, end)
    },

    File: {
      __builtin: true,
      read: (filePath) => {
        try {
          return fs.readFileSync(filePath, 'utf8');
        } catch (err) {
          throw new Error(`Failed to read file: ${err.message}`);
        }
      },
      write: (filePath, content) => {
        try {
          fs.writeFileSync(filePath, String(content), 'utf8');
          return true;
        } catch (err) {
          throw new Error(`Failed to write file: ${err.message}`);
        }
      },
      exists: (filePath) => {
        return fs.existsSync(filePath);
      },
      delete: (filePath) => {
        try {
          fs.unlinkSync(filePath);
          return true;
        } catch (err) {
          throw new Error(`Failed to delete file: ${err.message}`);
        }
      },
      readAsync: async (filePath) => {
        return new Promise((resolve, reject) => {
          fs.readFile(filePath, 'utf8', (err, data) => {
            if (err) reject(new Error(`Failed to read file: ${err.message}`));
            else resolve(data);
          });
        });
      },
      writeAsync: async (filePath, content) => {
        return new Promise((resolve, reject) => {
          fs.writeFile(filePath, String(content), 'utf8', (err) => {
            if (err) reject(new Error(`Failed to write file: ${err.message}`));
            else resolve(true);
          });
        });
      }
    },

    Http: {
      __builtin: true,
      get: (url) => {
        return new Promise((resolve, reject) => {
          const urlObj = new URL(url);
          const protocol = urlObj.protocol === 'https:' ? https : http;

          protocol.get(url, (res) => {
            let data = '';
            res.on('data', (chunk) => { data += chunk; });
            res.on('end', () => {
              resolve({
                status: res.statusCode,
                headers: res.headers,
                body: data
              });
            });
          }).on('error', (err) => {
            reject(new Error(`HTTP GET failed: ${err.message}`));
          });
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
            res.on('end', () => {
              resolve({
                status: res.statusCode,
                headers: res.headers,
                body: responseData
              });
            });
          });

          req.on('error', (err) => {
            reject(new Error(`HTTP POST failed: ${err.message}`));
          });

          req.write(data);
          req.end();
        });
      },
      // Note: fetch is added dynamically in the interpreter since it references this.variables
      _createFetch: function(httpObj) {
        return async (url, options = {}) => {
          const method = (options.method || 'GET').toUpperCase();
          if (method === 'POST' || method === 'PUT' || method === 'PATCH') {
            return httpObj.post(url, options.body || '');
          } else {
            return httpObj.get(url);
          }
        };
      }
    }
  };
}

module.exports = { initializeStandardLibrary };
