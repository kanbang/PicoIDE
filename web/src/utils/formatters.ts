/*
 * @Descripttion: 
 * @version: 0.x
 * @Author: zhai
 * @Date: 2026-02-08 19:01:54
 * @LastEditors: zhai
 * @LastEditTime: 2026-02-08 19:15:04
 */
/**
 * 格式化工具函数
 */

/**
 * 格式化文件大小
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

/**
 * 格式化时间
 */
export function formatTime(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (days > 0) {
    return `${days}天前`;
  } else if (hours > 0) {
    return `${hours}小时前`;
  } else if (minutes > 0) {
    return `${minutes}分钟前`;
  } else if (seconds > 0) {
    return `${seconds}秒前`;
  }
  return '刚刚';
}

/**
 * 格式化绝对时间
 */
export function formatAbsoluteTime(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  });
}

/**
 * 获取状态文本
 */
export function getStatusText(status: string): { text: string; color: string } {
  const statusMap: Record<string, { text: string; color: string }> = {
    running: { text: '运行中', color: '#4caf50' },
    completed: { text: '完成', color: '#007acc' },
    failed: { text: '失败', color: '#f44336' },
    stopping: { text: '停止中', color: '#ff9800' },
    stopped: { text: '已停止', color: '#999' }
  };
  return statusMap[status] || { text: status, color: '#999' };
}

/**
 * 获取文件类型图标
 */
export function getFileIconType(fileType: string): string {
  const iconMap: Record<string, string> = {
    'image': 'image',
    'video': 'video',
    'audio': 'audio',
    'document': 'document',
    'code': 'code',
    'json': 'code',
    'text': 'text',
    'data': 'database',
    'model': 'cube',
    'csv': 'table',
    'excel': 'table',
    'default': 'file'
  };
  return iconMap[fileType] || iconMap['default'];
}
