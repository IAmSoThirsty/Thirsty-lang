#!/usr/bin/env node

/**
 * Thirsty-Lang Enterprise Logger
 * =============================
 * Provides structured logging with levels and JSON formatting.
 */

'use strict';

class Logger {
    constructor(options = {}) {
        this.level = options.level || 'INFO';
        this.json = options.json !== false;
        this.component = options.component || 'CORE';

        this.LEVELS = {
            'DEBUG': 0,
            'INFO': 1,
            'WARN': 2,
            'ERROR': 3,
            'SECURITY': 4
        };
    }

    log(level, message, data = {}) {
        if (this.LEVELS[level] < this.LEVELS[this.level]) return;

        const entry = {
            timestamp: new Date().toISOString(),
            level,
            component: this.component,
            message,
            ...data
        };

        if (this.json) {
            console.log(JSON.stringify(entry));
        } else {
            console.log(`[${entry.timestamp}] [${level}] [${this.component}] ${message}`);
        }
    }

    debug(msg, data) { this.log('DEBUG', msg, data); }
    info(msg, data) { this.log('INFO', msg, data); }
    warn(msg, data) { this.log('WARN', msg, data); }
    error(msg, data) { this.log('ERROR', msg, data); }
    security(msg, data) { this.log('SECURITY', msg, data); }
}

module.exports = { Logger };
