import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import federation from '@originjs/vite-plugin-federation'

export default defineConfig({
  plugins: [
    vue(),
    federation({
      name: 'RsshubReader',
      filename: 'remoteEntry.js',
      exposes: {
        // 插件管理中点击卡片时加载的详情弹窗（缺失会导致“组件加载错误”）
        './Page': './src/Page.vue',
        // 插件管理中点击“设置”时加载的配置弹窗（含启用开关，缺失会导致“组件加载错误”）
        './Config': './src/Config.vue',
        // 主界面侧栏全页入口（nav_key=main）
        './AppPage': './src/AppPage.vue',
      },
      shared: {
        vue: {
          requiredVersion: false,
          generate: false,
        },
      },
      format: 'esm',
    }),
  ],
  build: {
    target: 'esnext',
    minify: false,
    cssCodeSplit: true,
  },
  css: {
    postcss: {
      plugins: [
        {
          postcssPlugin: 'internal:charset-removal',
          AtRule: {
            charset: atRule => {
              if (atRule.name === 'charset') {
                atRule.remove()
              }
            },
          },
        },
        {
          postcssPlugin: 'vuetify-filter',
          Root(root) {
            root.walkRules(rule => {
              if (!rule.selector) return
              // 只剔除「以 Vuetify/MDI 全局类开头」的选择器，避免污染宿主样式。
              // 形如 .entry-card .v-card-title / .app-page .v-btn 这类
              // 带插件自有类前缀的规则必须保留——它们是插件自己的样式，
              // 此前一律按包含 .v- 删除，导致卡片内边距、间距、触控尺寸等改动全部失效。
              // 注意：不能用 [data-v-] 判断，scoped 转换发生在 postcss 之后。
              const first = rule.selector.split(/[\s,>+~]+/)[0].trim()
              if (/^\.(v-|mdi-)/.test(first)) {
                rule.remove()
              }
            })
          },
        },
      ],
    },
  },
})
