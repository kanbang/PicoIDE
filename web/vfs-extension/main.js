exports.activate = function (context) {
  const vscode = require('vscode');

  class VFSProvider {
    constructor() {
      this._changeEmitter = new vscode.EventEmitter();
      this.onDidChangeFile = this._changeEmitter.event;
    }

    watch(uri, options) {
      return { dispose: () => {} };
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
      return entries.map(([name, type]) => [name, type === 2 ? vscode.FileType.Directory : vscode.FileType.File]);
    }

    async createDirectory(uri) {
      await fetch(`/api/vfs/mkdir?path=${encodeURIComponent(uri.path)}`, { method: 'POST' });
      this._changeEmitter.fire([{ type: vscode.FileChangeType.Created, uri }]);
    }

    async readFile(uri) {
      const res = await fetch(`/api/vfs/read?path=${encodeURIComponent(uri.path)}`);
      if (!res.ok) throw vscode.FileSystemError.FileNotFound(uri);
      const arrayBuffer = await res.arrayBuffer();
      return new Uint8Array(arrayBuffer);
    }

    async writeFile(uri, content, options) {
      const isNew = !options.create || options.create === false;
      await fetch(`/api/vfs/write?path=${encodeURIComponent(uri.path)}`, {
        method: 'POST',
        body: content
      });
      this._changeEmitter.fire([{ type: isNew ? vscode.FileChangeType.Changed : vscode.FileChangeType.Created, uri }]);
    }

    async delete(uri, options) {
      await fetch(`/api/vfs/delete?path=${encodeURIComponent(uri.path)}`, { method: 'DELETE' });
      this._changeEmitter.fire([{ type: vscode.FileChangeType.Deleted, uri }]);
    }

    async rename(oldUri, newUri, options) {
      // 先读取内容
      const content = await this.readFile(oldUri);
      // 写入新路径 (不触发事件)
      await fetch(`/api/vfs/write?path=${encodeURIComponent(newUri.path)}`, {
        method: 'POST',
        body: content
      });
      // 删除旧文件 (不触发事件)
      await fetch(`/api/vfs/delete?path=${encodeURIComponent(oldUri.path)}`, { method: 'DELETE' });
      // 触发重命名事件
      this._changeEmitter.fire([
        { type: vscode.FileChangeType.Deleted, uri: oldUri },
        { type: vscode.FileChangeType.Created, uri: newUri }
      ]);
    }
  }

  const provider = new VFSProvider();
  context.subscriptions.push(
    vscode.workspace.registerFileSystemProvider('vfs', provider, { isCaseSensitive: true })
  );
};