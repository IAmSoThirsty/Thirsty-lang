import * as path from 'path';
import { workspace, ExtensionContext } from 'vscode';
import {
    LanguageClient,
    LanguageClientOptions,
    ServerOptions,
    TransportKind
} from 'vscode-languageclient/node';

let client: LanguageClient;

export function activate(context: ExtensionContext) {
    // Get LSP server path from configuration
    const config = workspace.getConfiguration('thirstyLang');
    const serverPath = config.get<string>('lsp.serverPath') ||
        path.join(context.extensionPath, 'server', 'lsp_server.py');

    // Server options
    const serverOptions: ServerOptions = {
        command: 'python',
        args: [serverPath],
        transport: TransportKind.stdio
    };

    // Client options
    const clientOptions: LanguageClientOptions = {
        documentSelector: [{ scheme: 'file', language: 'thirsty' }],
        synchronize: {
            fileEvents: workspace.createFileSystemWatcher('**/.tarl')
        }
    };

    // Create and start the client
    client = new LanguageClient(
        'thirstyLangServer',
        'Thirsty-Lang Language Server',
        serverOptions,
        clientOptions
    );

    client.start();
}

export function deactivate(): Thenable<void> | undefined {
    if (!client) {
        return undefined;
    }
    return client.stop();
}
