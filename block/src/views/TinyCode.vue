<template>
  <div ref="container" class="tiny-code-editor" />
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

declare const require: any
declare const self: any

const container = ref<HTMLDivElement | null>(null)

onMounted(() => {
  if (!container.value) return

  // 动态添加 VS Code 主 CSS（保持不变）
  const cssLink = document.createElement('link')
  cssLink.rel = 'stylesheet'
  cssLink.href = '/vscode/out/vs/workbench/workbench.web.main.css'
  document.head.appendChild(cssLink)

  // 脚本加载工具函数
  const loadScript = (src?: string, text?: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      const script = document.createElement('script')
      if (src) script.src = src
      if (text) script.textContent = text
      script.type = 'text/javascript'
      script.onload = () => resolve()
      script.onerror = reject
      document.body.appendChild(script)
    })
  }

  // 异步加载 VS Code Web 资源（保持原顺序）
  ;(async () => {
    try {
      await loadScript('/vscode/out/vs/loader.js')
      await loadScript('/vscode/out/vs/webPackagePaths.js')

      await loadScript(undefined, `
        Object.keys(self.webPackagePaths).forEach(key => {
          self.webPackagePaths[key] = \`${window.location.origin}/vscode/node_modules/\${key}/\${self.webPackagePaths[key]}\`;
        });
        require.config({
          baseUrl: \`${window.location.origin}/vscode/out\`,
          recordStats: true,
          trustedTypesPolicy: window.trustedTypes?.createPolicy('amdLoader', { createScriptURL: v => v }),
          paths: self.webPackagePaths
        });
      `)

      await loadScript('/vscode/out/vs/workbench/workbench.web.main.nls.js')
      await loadScript('/vscode/out/vs/workbench/workbench.web.main.js')

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
        }

        wb.create(container.value!, {
          ...config,
          workspaceProvider: {
            trusted: true,
            workspace: {
              folderUri: wb.URI.from({ scheme: 'vfs', path: '/' })
            },
            async open() { return true }
          }
        })

        // 右键菜单清理（保持不变）
        const MENU_BLACKLIST = [
          /Outline/i, /大纲/i, /Timeline/i, /时间线/i,
          /Menu/i, /菜单/i, /Source Control/i, /源代码管理/i,
          /Run and Debug/i, /运行和调试/i, /Extensions/i, /扩展/i,
          /Accounts/i, /账户/i, /Move Primary Side Bar/i,
          /Hide Activity Bar/i, /Show Activity Bar/i
        ]

        const cleanupMenu = () => {
          const menu = document.querySelector('.monaco-menu-container, .context-view')
          if (!menu) return

          const items = Array.from(menu.querySelectorAll('.action-item'))
          items.forEach(item => {
            const label = item.querySelector('.action-label')
            const text = (label?.textContent || '') + (label?.getAttribute('aria-label') || '')

            if (MENU_BLACKLIST.some(regex => regex.test(text))) {
              item.style.display = 'none'
              item.hidden = true
            }
          })
        }

        const observer = new MutationObserver(() => {
          requestAnimationFrame(cleanupMenu)
        })
        observer.observe(document.body, { childList: true, subtree: true, attributes: true })
      })

      await loadScript('/vscode/out/vs/code/browser/workbench/workbench.js')
    } catch (err) {
      console.error('加载 VS Code Web 资源失败', err)
    }
  })()
})
</script>

<style scoped>
.tiny-code-editor {
  width: 100%;
  height: 100vh;
}
</style>

<!-- 全局样式：隐藏 VS Code 不需要的 UI 元素（无 scoped，确保生效） -->
<style>
/* 隐藏活动栏不必要图标 */
.action-item:has(a[aria-label^="Menu"]),
.action-item:has(a[aria-label^="菜单"]),
.activitybar .content .home-bar,
.composite-bar .home-bar,
.action-item:has(a[aria-label^="Source Control"]),
.action-item:has(a[aria-label^="源代码管理"]),
.action-item:has(a[aria-label^="Run and Debug"]),
.action-item:has(a[aria-label^="运行和调试"]),
.action-item:has(a[aria-label^="Extensions"]),
.action-item:has(a[aria-label^="扩展"]),
.action-item:has(a[aria-label^="Accounts"]),
.action-item:has(a[aria-label^="账户"]),
.action-item:has(a[aria-label^="Manage"]),
.action-item:has(a[aria-label^="管理"]) {
    display: none !important;
}

/* 隐藏状态栏 */
.monaco-workbench .statusbar {
    display: none !important;
}

/* 隐藏 Outline、Timeline 等视图 */
.pane-header:has([title="Outline"]),
.pane-header:has([title="Timeline"]),
.pane-header:has([title="大纲"]),
.pane-header:has([title="时间线"]) {
    display: none !important;
}

.view-instance .outline-tree,
.view-instance .timeline-tree {
    display: none !important;
}
</style>