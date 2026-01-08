exports.activate = function (context) {
    const vscode = require('vscode');

    class VFSProvider {
        constructor() {
            this._emitter = new vscode.EventEmitter();
            this.onDidChangeFile = this._emitter.event;
        }

        watch(uri, options) {
            // 不实现实时监听，VS Code 会轮询（大多数虚拟 FS 都这样）
            return { dispose: () => { } };
        }

        _getParentUri(uri) {
            if (uri.path === '/' || uri.path === '') return null;
            const parentPath = uri.path.replace(/\/[^\/]*\/?$/, '/');
            return parentPath === '/' ? uri.with({ path: '/' }) : uri.with({ path: parentPath });
        }

        _fireSoon(...changes) {
            // 批量触发事件，避免短时间内重复触发
            this._emitter.fire(changes);
        }

        async stat(uri) {
            const res = await fetch(`/api/vfs/stat?path=${encodeURIComponent(uri.path)}`);
            if (!res.ok) throw vscode.FileSystemError.FileNotFound(uri);
            const data = await res.json();
            return {
                type: data.type === 2 ? vscode.FileType.Directory : vscode.FileType.File,
                ctime: data.ctime,
                mtime: data.mtime,
                size: data.size
            };
        }

        async readDirectory(uri) {
            const res = await fetch(`/api/vfs/readdir?path=${encodeURIComponent(uri.path)}`);
            if (!res.ok) throw vscode.FileSystemError.FileNotFound(uri);
            const entries = await res.json();
            return entries.map(([name, type]) => [
                name,
                type === 2 ? vscode.FileType.Directory : vscode.FileType.File
            ]);
        }

        async createDirectory(uri) {
            const res = await fetch(`/api/vfs/mkdir?path=${encodeURIComponent(uri.path)}`, { method: 'POST' });
            if (!res.ok) throw vscode.FileSystemError.Unavailable('Failed to create directory');

            this._fireSoon(
                { type: vscode.FileChangeType.Created, uri },
                { type: vscode.FileChangeType.Changed, uri: this._getParentUri(uri) || uri }
            );
        }

        async readFile(uri) {
            const res = await fetch(`/api/vfs/read?path=${encodeURIComponent(uri.path)}`);
            if (!res.ok) throw vscode.FileSystemError.FileNotFound(uri);
            const arrayBuffer = await res.arrayBuffer();
            return new Uint8Array(arrayBuffer);
        }

        async writeFile(uri, content, options) {
            // 严格遵守 VS Code 选项语义
            let existed = false;
            try {
                await this.stat(uri);
                existed = true;
            } catch (err) {
                if (!(err instanceof vscode.FileSystemError && err.code === 'FileNotFound')) {
                    throw err;
                }
            }

            if (existed && !options.overwrite) {
                throw vscode.FileSystemError.FileExists(uri);
            }
            if (!existed && !options.create) {
                throw vscode.FileSystemError.FileNotFound(uri);
            }

            const res = await fetch(`/api/vfs/write?path=${encodeURIComponent(uri.path)}`, {
                method: 'POST',
                body: content
            });
            if (!res.ok) throw vscode.FileSystemError.Unavailable('Failed to write file');

            const changeType = existed ? vscode.FileChangeType.Changed : vscode.FileChangeType.Created;
            this._fireSoon(
                { type: changeType, uri },
                { type: vscode.FileChangeType.Changed, uri: this._getParentUri(uri) || uri }
            );
        }

        async delete(uri, options) {
            const stat = await this.stat(uri);

            if (stat.type === vscode.FileType.Directory && !options.recursive) {
                const entries = await this.readDirectory(uri);
                if (entries.length > 0) {
                    throw new vscode.FileSystemError('Directory is not empty.');
                }
            }

            const res = await fetch(`/api/vfs/delete?path=${encodeURIComponent(uri.path)}`, { method: 'DELETE' });
            if (!res.ok) throw vscode.FileSystemError.Unavailable('Failed to delete');

            this._fireSoon(
                { type: vscode.FileChangeType.Deleted, uri },
                { type: vscode.FileChangeType.Changed, uri: this._getParentUri(uri) || uri }
            );
        }

        async rename(oldUri, newUri, options) {
            // 先检查目标是否已存在
            let targetExists = false;
            try {
                await this.stat(newUri);
                targetExists = true;
            } catch (err) {
                if (!(err instanceof vscode.FileSystemError && err.code === 'FileNotFound')) {
                    throw err;
                }
            }

            if (targetExists && !options.overwrite) {
                throw vscode.FileSystemError.FileExists(newUri);
            }

            // 执行完整递归移动（支持文件和目录）
            await this._move(oldUri, newUri);

            // 触发父目录变更（如果父目录不同）
            const oldParent = this._getParentUri(oldUri);
            const newParent = this._getParentUri(newUri);
            const changes = [
                { type: vscode.FileChangeType.Deleted, uri: oldUri },
                { type: vscode.FileChangeType.Created, uri: newUri }
            ];
            if (oldParent) changes.push({ type: vscode.FileChangeType.Changed, uri: oldParent });
            if (newParent && (!oldParent || newParent.toString() !== oldParent.toString())) {
                changes.push({ type: vscode.FileChangeType.Changed, uri: newParent });
            }
            this._fireSoon(...changes);
        }

        async _move(oldUri, newUri) {
            const oldStat = await this.stat(oldUri);

            if (oldStat.type === vscode.FileType.File) {
                const content = await this.readFile(oldUri);
                // 使用 {create: true, overwrite: true} 确保目标可覆盖
                await this.writeFile(newUri, content, { create: true, overwrite: true });
                await this.delete(oldUri, { recursive: true });
            } else {
                // 目录：先创建目标目录
                await this.createDirectory(newUri);

                // 递归移动所有直接子项
                const entries = await this.readDirectory(oldUri);
                for (const [name, type] of entries) {
                    const oldChildPath = oldUri.path.endsWith('/') ? oldUri.path + name : oldUri.path + '/' + name;
                    const newChildPath = newUri.path.endsWith('/') ? newUri.path + name : newUri.path + '/' + name;

                    const oldChildUri = oldUri.with({
                        path: type === vscode.FileType.Directory ? oldChildPath + '/' : oldChildPath
                    });
                    const newChildUri = newUri.with({
                        path: type === vscode.FileType.Directory ? newChildPath + '/' : newChildPath
                    });

                    await this._move(oldChildUri, newChildUri);
                }

                // 最后删除原目录（后端会递归删除剩余空目录）
                await this.delete(oldUri, { recursive: true });
            }
        }
    }

    const provider = new VFSProvider();
    context.subscriptions.push(
        vscode.workspace.registerFileSystemProvider('vfs', provider, { isCaseSensitive: true, isReadonly: false })
    );
};