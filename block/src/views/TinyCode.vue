<template>
  <div ref="editorContainer" class="tiny-code-editor-root"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue';

/**
 * 声明外部依赖的全局变量
 */
declare const require: any;
declare const self: any;
declare const window: any;

const editorContainer = ref<HTMLElement | null>(null);
let menuObserver: MutationObserver | null = null;

/**
 * 1. 动态加载资源
 * 模拟 HTML 中的 <link> 和 <script> 标签加载
 */
const loadDependencies = (): Promise<void> => {
  return new Promise((resolve) => {
    // 加载 CSS
    if (!document.querySelector('link[data-name="vs/workbench/workbench.web.main"]')) {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.dataset.name = 'vs/workbench/workbench.web.main';
      link.href = './vscode/out/vs/workbench/workbench.web.main.css';
      document.head.appendChild(link);
    }

    // 顺序加载 JS 脚本
    const scripts = [
      './vscode/out/vs/loader.js',
      './vscode/out/vs/webPackagePaths.js',
      './vscode/out/vs/workbench/workbench.web.main.nls.js',
      './vscode/out/vs/workbench/workbench.web.main.js',
      './vscode/out/vs/code/browser/workbench/workbench.js'
    ];

    let loadedCount = 0;
    const loadNext = () => {
      const script = document.createElement('script');
      script.src = scripts[loadedCount];
      script.async = false; // 保证按顺序执行
      script.onload = () => {
        loadedCount++;
        if (loadedCount < scripts.length) {
          loadNext();
        } else {
          resolve();
        }
      };
      document.body.appendChild(script);
    };
    loadNext();
  });
};

/**
 * 2. 增强型右键菜单清理逻辑
 */
const MENU_BLACKLIST = [
  /Outline/i, /大纲/i, /Timeline/i, /时间线/i,
  /Menu/i, /菜单/i, /Source Control/i, /源代码管理/i,
  /Run and Debug/i, /运行和调试/i, /Extensions/i, /扩展/i,
  /Accounts/i, /账户/i, /Move Primary Side Bar/i,
  /Hide Activity Bar/i, /Show Activity Bar/i
];

const cleanupMenu = () => {
  const menu = document.querySelector('.monaco-menu-container, .context-view');
  if (!menu) return;

  const items = Array.from(menu.querySelectorAll<HTMLElement>('.action-item'));
  items.forEach(item => {
    const label = item.querySelector('.action-label');
    const text = (label?.textContent || '') + (label?.getAttribute('aria-label') || '');

    const shouldHide = MENU_BLACKLIST.some(regex => regex.test(text));
    if (shouldHide) {
      item.style.display = 'none';
      item.hidden = true;
      return;
    }

    if (item.classList.contains('separator') || (text.trim() === '' && item.classList.contains('disabled'))) {
      item.classList.add('menu-separator');
    }
  });

  const visibleItems = items.filter(i => window.getComputedStyle(i).display !== 'none' && !i.hidden);
  if (visibleItems.length > 0) {
    if (visibleItems[0].classList.contains('menu-separator')) visibleItems[0].style.display = 'none';
    if (visibleItems[visibleItems.length - 1].classList.contains('menu-separator')) visibleItems[visibleItems.length - 1].style.display = 'none';
  }
};

/**
 * 3. 初始化 VS Code Workbench
 */
const initVSCode = () => {
  // 配置路径
  if (self.webPackagePaths) {
    Object.keys(self.webPackagePaths).forEach(key => {
      self.webPackagePaths[key] = `${window.location.origin}/vscode/node_modules/${key}/${self.webPackagePaths[key]}`;
    });
  }

  require.config({
    baseUrl: `${window.location.origin}/vscode/out`,
    recordStats: true,
    trustedTypesPolicy: window.trustedTypes?.createPolicy('amdLoader', {
      createScriptURL: (v: string) => v
    }),
    paths: self.webPackagePaths
  });

  require(['vs/workbench/workbench.web.main'], (wb: any) => {
    const config = {
      additionalBuiltinExtensions: [
        wb.URI.from({
          scheme: location.protocol.replace(':', ''),
          authority: location.host || '',
          path: '/vfs-extension'
        })
      ],
      productConfiguration: { extensionsGallery: undefined },
      configurationDefaults: {
        "workbench.colorTheme": "Default Dark+",
        "workbench.activityBar.visible": true,
        "workbench.statusBar.visible": false,
        "workbench.layoutControl.enabled": false,
        "window.commandCenter": false,
        "window.menuBarVisibility": "hidden",
        "workbench.startupEditor": "none",
        "workbench.editor.enablePreview": false,
        "outline.enabled": false,
        "timeline.enabled": false,
        "scm.enabled": false,
        "debug.enabled": false,
        "extensions.enabled": false,
        "workbench.view.explorer.visible": true,
        "workbench.view.search.visible": true
      }
    };

    wb.create(editorContainer.value, {
      ...config,
      workspaceProvider: {
        trusted: true,
        workspace: {
          folderUri: wb.URI.from({ scheme: 'vfs', path: '/' })
        },
        async open() { return true; }
      }
    });
  });
};

onMounted(async () => {
  // 加载脚本与样式
  await loadDependencies();
  
  // 初始化编辑器
  initVSCode();

  // 启动 UI 监听
  menuObserver = new MutationObserver(() => {
    requestAnimationFrame(cleanupMenu);
  });
  menuObserver.observe(document.body, { childList: true, subtree: true, attributes: true });
});

onBeforeUnmount(() => {
  menuObserver?.disconnect();
  // 注意：VS Code Workbench 销毁逻辑较为复杂，通常建议在单页应用中使用 iframe 隔离，
  // 或者在此处进行必要的 DOM 清理。
});
</script>

<style scoped>
.tiny-code-editor-root {
  width: 100%;
  height: 100vh;
  background-color: #1e1e1e;
  overflow: hidden;
}

/* 使用 :deep 深度选择器，因为 VS Code 的 DOM 是在组件运行后生成的 
*/
:deep(.action-item:has(a[aria-label^="Menu"])),
:deep(.action-item:has(a[aria-label^="菜单"])),
:deep(.activitybar .content .home-bar),
:deep(.composite-bar .home-bar) {
  display: none !important;
}

:deep(.action-item:has(a[aria-label^="Source Control"])),
:deep(.action-item:has(a[aria-label^="源代码管理"])),
:deep(.action-item:has(a[aria-label^="Run and Debug"])),
:deep(.action-item:has(a[aria-label^="运行和调试"])),
:deep(.action-item:has(a[aria-label^="Extensions"])),
:deep(.action-item:has(a[aria-label^="扩展"])),
:deep(.action-item:has(a[aria-label^="Accounts"])),
:deep(.action-item:has(a[aria-label^="账户"])),
:deep(.action-item:has(a[aria-label^="Manage"])),
:deep(.action-item:has(a[aria-label^="管理"])) {
  display: none !important;
}

:deep(.monaco-workbench .statusbar) {
  display: none !important;
}

:deep(.pane-header:has([title="Outline"])),
:deep(.pane-header:has([title="Timeline"])),
:deep(.pane-header:has([title="大纲"])),
:deep(.pane-header:has([title="时间线"])) {
  display: none !important;
}

:deep(.view-instance .outline-tree),
:deep(.view-instance .timeline-tree) {
  display: none !important;
}
</style>