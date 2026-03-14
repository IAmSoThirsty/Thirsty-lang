/**
 * Thirsty-Lang Database Bridge
 * Provides native SQLite support for Sovereign-grade persistence.
 */

const sqlite3 = require('sqlite3').verbose();
const path = require('path');

class ThirstyDB {
  constructor(dbPath) {
    this.dbPath = path.resolve(dbPath);
    this.db = null;
    this.__builtin = true;
  }

  /**
   * Open the database connection
   */
  open() {
    return new Promise((resolve, reject) => {
      this.db = new sqlite3.Database(this.dbPath, (err) => {
        if (err) reject(new Error(`Failed to open database: ${err.message}`));
        else resolve(true);
      });
    });
  }

  /**
   * Execute a query that doesn't return rows (INSERT, UPDATE, DELETE)
   */
  run(query, params = []) {
    return new Promise((resolve, reject) => {
      if (!this.db) return reject(new Error("Database not open"));
      this.db.run(query, params, function(err) {
        if (err) reject(new Error(`Query failed: ${err.message}`));
        else resolve({ lastID: this.lastID, changes: this.changes });
      });
    });
  }

  /**
   * Get a single row from a query result
   */
  get(query, params = []) {
    return new Promise((resolve, reject) => {
      if (!this.db) return reject(new Error("Database not open"));
      this.db.get(query, params, (err, row) => {
        if (err) reject(new Error(`Query failed: ${err.message}`));
        else resolve(row);
      });
    });
  }

  /**
   * Get all rows from a query result
   */
  all(query, params = []) {
    return new Promise((resolve, reject) => {
      if (!this.db) return reject(new Error("Database not open"));
      this.db.all(query, params, (err, rows) => {
        if (err) reject(new Error(`Query failed: ${err.message}`));
        else resolve(rows);
      });
    });
  }

  /**
   * Close the database connection
   */
  close() {
    return new Promise((resolve, reject) => {
      if (!this.db) return resolve(true);
      this.db.close((err) => {
        if (err) reject(new Error(`Failed to close database: ${err.message}`));
        else {
          this.db = null;
          resolve(true);
        }
      });
    });
  }
}

/**
 * Initialize Database module
 */
function initializeDB() {
  return {
    __builtin: true,
    connect: (dbPath) => {
      const db = new ThirstyDB(dbPath);
      return db;
    }
  };
}

module.exports = { initializeDB, ThirstyDB };
