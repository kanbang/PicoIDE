<template>
  <div ref="workbenchContainer" class="tiny-code-container"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue';

// --- 类型定义 ---
interface VSCodeWorkbench {
  create(container: HTMLElement, config: any): void;
  URI: {
    from(components: { scheme: string; authority?: string; path: string }): any;
  };
}

// 声明全局变量（由 vscode loader 加载）
declare const require: any;
declare const self: any;

const workbenchContainer = ref<HTMLElement | null>(null);
let observer: MutationObserver | null = null;

// --- 右键菜单与 UI 清理逻辑 ---
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
      item.style.setProperty('display', 'none', 'important');
      item.hidden = true;
    }
    
    if (item.classList.contains('separator')) {
      item.classList.add('menu-separator');
    }
  });

  // 处理多余的分隔线
  const visibleItems = items.filter(i => 
    window.getComputedStyle(i).display !== 'none' && !i.hidden
  );

  if (visibleItems.length > 0) {
    if (visibleItems[0].classList.contains('menu-separator')) visibleItems[0].style.display = 'none';
    if (visibleItems[visibleItems.length - 1].classList.contains('menu-separator')) visibleItems[visibleItems.length - 1].style.display = 'none';
  }
};

// --- 初始化 Workbench ---
const initWorkbench = (wb: VSCodeWorkbench) => {
  if (!workbenchContainer.value) return;

  const config = {
    additionalBuiltinExtensions: [
      wb.URI.from({
        scheme: window.location.protocol.replace(':', ''),
        authority: window.location.host || '',
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
    },
    workspaceProvider: {
      trusted: true,
      workspace: {
        folderUri: wb.URI.from({ scheme: 'vfs', path: '/' })
      },
      async open() { return true; }
    }
  };

  wb.create(workbenchContainer.value, config);
};

onMounted(() => {
  // 1. 设置 AMD Loader 配置
  if (typeof self.webPackagePaths !== 'undefined') {
    Object.keys(self.webPackagePaths).forEach(key => {
      self.webPackagePaths[key] = `${window.location.origin}/vscode/node_modules/${key}/${self.webPackagePaths[key]}`;
    });
  }

  require.config({
    baseUrl: `${window.location.origin}/vscode/out`,
    paths: self.webPackagePaths
  });

  // 2. 加载并启动
  require(['vs/workbench/workbench.web.main'], (wb: VSCodeWorkbench) => {
    initWorkbench(wb);
  });

  // 3. 启动 DOM 监听器进行 UI 微调
  observer = new MutationObserver(() => {
    requestAnimationFrame(cleanupMenu);
  });
  observer.observe(document.body, { 
    childList: true, 
    subtree: true, 
    attributes: true 
  });
});

onBeforeUnmount(() => {
  observer?.disconnect();
});
</script>

<style scoped>
.tiny-code-container {
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}

/* 使用 :deep 穿透修改 VS Code 内部样式 */
:deep(.action-item:has(a[aria-label^="Menu"])),
:deep(.action-item:has(a[aria-label^="菜单"])),
:deep(.activitybar .content .home-bar) {
  display: none !important;
}

:deep(.monaco-workbench .statusbar) {
  display: none !important;
}

/* 更多 CSS 逻辑可在此处按需迁移... */
</style>