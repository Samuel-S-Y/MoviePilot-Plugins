<script>
// 插件管理「详情弹窗」组件（联邦暴露名 ./Page）
// 宿主在「我的插件」中点击插件卡片时加载本组件；
// 完整功能在侧栏全页 AppPage 中，本组件只做简介、统计与入口跳转。

// 重要：MP 的插件 ID 是后端插件「类名」（plugin_id = plugin.__name__），
// 即 RsshubReader，而不是插件目录名 rsshub_reader；
// 且宿主详情弹窗（PluginDataDialog）不会向远程组件传入 pluginId，
// 因此这里必须使用与后端类名一致的常量，否则 API 路径 404、全页跳转失败。
const PLUGIN_ID = "RsshubReader";

// 兼容 MP 插件 API 响应的两种形态：
// 1) 包装形态 {success: true, data: {...}} -> 取 data；
// 2) 端点直接返回 {ok: true, ...} -> 原样返回。
function unwrapResponse(res) {
  if (res && typeof res === "object" && "success" in res && "data" in res) {
    return res.data;
  }
  return res;
}

export default {
  name: "RsshubReaderPage",
  // 宿主注入：api 为 bear 认证调用器；详情弹窗不传 pluginId，默认值必须为类名
  props: {
    api: { type: Object, default: () => ({}) },
    pluginId: { type: String, default: PLUGIN_ID },
    nativeSubscribe: { type: Function, default: null },
    // 宿主（PluginDataDialog）控制是否允许切换到配置页；默认允许
    show_switch: { type: Boolean, default: true },
  },
  // 弹窗约定事件：action 通知宿主刷新、switch 切换到配置弹窗、close 关闭弹窗
  emits: ["action", "switch", "close"],
  data() {
    return {
      feedCount: 0, // 订阅源总数
      unreadCount: 0, // 全部源未读条目数
      loading: false, // 统计加载中
      refreshing: false, // 手动刷新中
      errorMsg: "", // 页面内错误提示
      // 功能特性清单（仅展示用）
      features: [
        { icon: "mdi-rss", text: "订阅源管理，支持 OPML 导入/导出" },
        { icon: "mdi-image-multiple", text: "抓取正文完整图片，后端代理绕过防盗链" },
        { icon: "mdi-check-circle-outline", text: "已读/未读标记与未读数统计" },
        { icon: "mdi-bell-outline", text: "关键词/正则规则命中后消息通知" },
      ],
    };
  },
  computed: {
    // 统一使用真实插件 ID（优先宿主传入，缺省回退类名常量）
    realPluginId() {
      return this.pluginId || PLUGIN_ID;
    },
    // 插件 API 基础路径（MP 统一挂载在 /api/v1/plugin/ 下）
    pluginBase() {
      return "plugin/" + this.realPluginId;
    },
  },
  mounted() {
    this.loadStats();
  },
  methods: {
    // 拉取全源概览，统计订阅源数量与未读总数
    async loadStats() {
      this.loading = true;
      this.errorMsg = "";
      try {
        const res = await this.api.get(this.pluginBase + "/articles");
        const data = unwrapResponse(res);
        if (data && data.ok) {
          const feeds = data.feeds || [];
          this.feedCount = feeds.length;
          this.unreadCount = feeds.reduce((sum, f) => sum + (f.unread || 0), 0);
        }
      } catch (e) {
        // 路由不存在（如插件更新后未重载）时给出可操作的引导，其余异常显示原文
        const status = e && e.response && e.response.status;
        if (status === 404) {
          this.errorMsg = "插件接口未就绪，请在「设置」中保存配置以启用插件，必要时重启 MoviePilot 后重试";
        } else {
          this.errorMsg = "暂无法读取订阅数据：" + (e.message || e);
        }
      } finally {
        this.loading = false;
      }
    },
    // 手动触发后端全量刷新，完成后刷新统计
    async refreshAll() {
      this.refreshing = true;
      this.errorMsg = "";
      try {
        const res = await this.api.post(this.pluginBase + "/refresh", {});
        const data = unwrapResponse(res);
        if (data && data.ok === false) {
          this.errorMsg = data.msg || "刷新失败";
        } else {
          await this.loadStats();
        }
      } catch (e) {
        const status = e && e.response && e.response.status;
        this.errorMsg =
          status === 404
            ? "插件接口未就绪，请先在「设置」中启用插件"
            : "刷新失败：" + (e.message || e);
      } finally {
        this.refreshing = false;
      }
    },
    // 切换到宿主配置弹窗（MP v2 无独立启用按钮，在配置页保存含 enabled 的配置即启用）
    openConfig() {
      this.$emit("switch");
    },
    // 跳转到侧栏全页应用（路由约定 #/plugin-app/<插件类名>/<navKey>），并关闭弹窗
    openAppPage() {
      window.location.hash = "#/plugin-app/" + this.realPluginId + "/main";
      this.$emit("close");
    },
  },
};
</script>

<template>
  <div class="rsshub-page pa-4">
    <!-- 顶部：图标 + 名称 + 简介 -->
    <div class="d-flex align-center mb-3">
      <v-icon size="30" color="primary" class="mr-3">mdi-rss-box</v-icon>
      <div>
        <div class="text-h6">RSSHub 阅读器</div>
        <div class="text-caption text-medium-emphasis">
          订阅源管理 · 文章阅读 · 规则通知
        </div>
      </div>
    </div>

    <!-- 统计卡片：订阅源 / 未读数 -->
    <v-row dense>
      <v-col cols="6">
        <v-card variant="tonal" color="primary" :loading="loading">
          <v-card-text class="py-3 text-center">
            <div class="text-h5">{{ feedCount }}</div>
            <div class="text-caption">订阅源</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="6">
        <v-card variant="tonal" color="warning" :loading="loading">
          <v-card-text class="py-3 text-center">
            <div class="text-h5">{{ unreadCount }}</div>
            <div class="text-caption">未读文章</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- 错误提示（接口不可用时的页面内降级，不阻断弹窗） -->
    <v-alert
      v-if="errorMsg"
      type="error"
      variant="tonal"
      density="compact"
      class="mt-3"
    >
      {{ errorMsg }}
    </v-alert>

    <!-- 功能特性列表 -->
    <v-list density="compact" class="my-2">
      <v-list-item v-for="item in features" :key="item.text">
        <template #prepend>
          <v-icon color="primary">{{ item.icon }}</v-icon>
        </template>
        <v-list-item-title class="text-body-2">{{ item.text }}</v-list-item-title>
      </v-list-item>
    </v-list>

    <!-- 操作区：打开全页 / 设置（启用入口）/ 立即刷新 / 关闭 -->
    <div class="d-flex flex-wrap align-center mt-3">
      <v-btn color="primary" variant="flat" @click="openAppPage">
        <v-icon start>mdi-open-in-new</v-icon>打开 RSS 阅读器
      </v-btn>
      <v-btn v-if="show_switch" class="ml-2" variant="outlined" @click="openConfig">
        <v-icon start>mdi-cog-outline</v-icon>设置
      </v-btn>
      <v-btn
        class="ml-2"
        variant="outlined"
        :loading="refreshing"
        @click="refreshAll"
      >
        <v-icon start>mdi-refresh</v-icon>立即刷新
      </v-btn>
      <v-spacer />
      <v-btn variant="text" @click="$emit('close')">关闭</v-btn>
    </div>
  </div>
</template>
