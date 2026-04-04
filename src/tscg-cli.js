#!/usr/bin/env node

/**
 * TSCG CLI - Command-line interface for TSCG compression
 *
 * Usage:
 *   thirsty-compress <command> [options]
 *
 * Commands:
 *   compress <dir> <output>    Compress repository to TSCG-B binary
 *   decompress <input> <dir>   Decompress TSCG-B binary to repository
 *   micro <file> <output>      Compress single file to micro payload
 *   analyze <dir>              Analyze repository without compressing
 *   verify <file>              Verify TSCG-B file integrity
 *   export <input> <output>    Export TSCG-B to JSON
 *   import <input> <output>    Import JSON to TSCG-B
 */

const TSCGManager = require('./tscg/index');
const path = require('path');

// Parse command line arguments
const args = process.argv.slice(2);
const command = args[0];

// Create TSCG manager
const manager = new TSCGManager();

// Display header
function displayHeader() {
  console.log(`
╔════════════════════════════════════════════════════════╗
║                                                        ║
║   💧 TSCG - Thirsty Symbolic Compression Grammar      ║
║                                                        ║
║   Tier 5: Symbolic Compression                        ║
║   Tier 6: Binary Encoding (TSCG-B)                    ║
║                                                        ║
╚════════════════════════════════════════════════════════╝
  `);
}

// Display usage
function displayUsage() {
  console.log(`
Usage: thirsty-compress <command> [options]

Commands:
  compress <dir> <output>      Compress repository to TSCG-B binary
                               Example: thirsty-compress compress ./src repo.tscg

  decompress <input> <dir>     Decompress TSCG-B binary to repository
                               Example: thirsty-compress decompress repo.tscg ./output

  micro <file> <output>        Compress single file to micro payload (~20 bytes)
                               Example: thirsty-compress micro hello.thirsty hello.tscg

  analyze <dir>                Analyze repository without compressing
                               Example: thirsty-compress analyze ./src

  verify <file>                Verify TSCG-B file integrity
                               Example: thirsty-compress verify repo.tscg

  export <input> <output>      Export TSCG-B to JSON for inspection
                               Example: thirsty-compress export repo.tscg repo.json

  import <input> <output>      Import JSON to TSCG-B binary
                               Example: thirsty-compress import repo.json repo.tscg

Options:
  --include-hidden             Include hidden files (default: false)
  --no-git-aware               Disable .gitignore awareness (default: git-aware)
  --ext <extensions>           Filter by extensions (comma-separated)
                               Example: --ext .js,.ts,.thirsty

Examples:
  # Compress entire repository
  thirsty-compress compress . my-repo.tscg

  # Compress only Thirsty-lang files
  thirsty-compress compress . thirsty-only.tscg --ext .thirsty,.thirstyplus,.thirstyplusplus

  # Decompress to new directory
  thirsty-compress decompress my-repo.tscg ./restored

  # Create ultra-compact micro payload
  thirsty-compress micro examples/hello.thirsty hello.tscg

  # Verify integrity
  thirsty-compress verify my-repo.tscg

  # Analyze repository size
  thirsty-compress analyze .
  `);
}

// Parse options
function parseOptions(args) {
  const options = {
    includeHidden: false,
    gitAware: true,
    extensions: null,
  };

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--include-hidden') {
      options.includeHidden = true;
    } else if (args[i] === '--no-git-aware') {
      options.gitAware = false;
    } else if (args[i] === '--ext' && args[i + 1]) {
      options.extensions = args[i + 1].split(',').map(ext => ext.trim());
      i++;
    }
  }

  return options;
}

// Main command handler
function main() {
  displayHeader();

  if (!command || command === 'help' || command === '--help' || command === '-h') {
    displayUsage();
    process.exit(0);
  }

  try {
    switch (command) {
      case 'compress': {
        const dirPath = args[1];
        const outputPath = args[2];

        if (!dirPath || !outputPath) {
          console.error('Error: Missing arguments for compress command');
          console.log('\nUsage: thirsty-compress compress <dir> <output>');
          process.exit(1);
        }

        const options = parseOptions(args.slice(3));
        const result = manager.compressRepository(
          path.resolve(dirPath),
          path.resolve(outputPath),
          options
        );

        console.log(`\n✨ Compression complete!`);
        process.exit(0);
        break;
      }

      case 'decompress': {
        const inputPath = args[1];
        const dirPath = args[2];

        if (!inputPath || !dirPath) {
          console.error('Error: Missing arguments for decompress command');
          console.log('\nUsage: thirsty-compress decompress <input> <dir>');
          process.exit(1);
        }

        const options = parseOptions(args.slice(3));
        const result = manager.decompressRepository(
          path.resolve(inputPath),
          path.resolve(dirPath),
          options
        );

        console.log(`\n✨ Decompression complete!`);
        process.exit(0);
        break;
      }

      case 'micro': {
        const filePath = args[1];
        const outputPath = args[2];

        if (!filePath || !outputPath) {
          console.error('Error: Missing arguments for micro command');
          console.log('\nUsage: thirsty-compress micro <file> <output>');
          process.exit(1);
        }

        const result = manager.compressMicroPayload(
          path.resolve(filePath),
          path.resolve(outputPath)
        );

        console.log(`\n✨ Micro payload created!`);
        if (result.compressedSize <= 30) {
          console.log(`🎯 Target achieved: ${result.compressedSize} bytes!`);
        }
        process.exit(0);
        break;
      }

      case 'analyze': {
        const dirPath = args[1];

        if (!dirPath) {
          console.error('Error: Missing arguments for analyze command');
          console.log('\nUsage: thirsty-compress analyze <dir>');
          process.exit(1);
        }

        const options = parseOptions(args.slice(2));
        const result = manager.analyzeRepository(path.resolve(dirPath), options);

        console.log(`\n✨ Analysis complete!`);
        process.exit(0);
        break;
      }

      case 'verify': {
        const filePath = args[1];

        if (!filePath) {
          console.error('Error: Missing arguments for verify command');
          console.log('\nUsage: thirsty-compress verify <file>');
          process.exit(1);
        }

        const result = manager.verifyCompressed(path.resolve(filePath));

        if (result.valid) {
          console.log(`\n✨ Verification successful!`);
          process.exit(0);
        } else {
          console.log(`\n❌ Verification failed!`);
          process.exit(1);
        }
        break;
      }

      case 'export': {
        const inputPath = args[1];
        const outputPath = args[2];

        if (!inputPath || !outputPath) {
          console.error('Error: Missing arguments for export command');
          console.log('\nUsage: thirsty-compress export <input> <output>');
          process.exit(1);
        }

        const result = manager.exportJSON(
          path.resolve(inputPath),
          path.resolve(outputPath)
        );

        console.log(`\n✨ Export complete!`);
        process.exit(0);
        break;
      }

      case 'import': {
        const inputPath = args[1];
        const outputPath = args[2];

        if (!inputPath || !outputPath) {
          console.error('Error: Missing arguments for import command');
          console.log('\nUsage: thirsty-compress import <input> <output>');
          process.exit(1);
        }

        const result = manager.importJSON(
          path.resolve(inputPath),
          path.resolve(outputPath)
        );

        console.log(`\n✨ Import complete!`);
        process.exit(0);
        break;
      }

      default:
        console.error(`Error: Unknown command '${command}'`);
        displayUsage();
        process.exit(1);
    }
  } catch (error) {
    console.error(`\n❌ Error: ${error.message}`);
    if (process.env.DEBUG) {
      console.error(error.stack);
    }
    process.exit(1);
  }
}

// Run CLI
main();
