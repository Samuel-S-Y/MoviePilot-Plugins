<script>
// 插件配置弹窗组件（联邦暴露名 ./Config）
// 宿主在「我的插件 → 设置」中加载本组件；
// MP v2 没有独立的「启用」按钮：保存含 enabled=true 的配置即启用插件，
// 因此本组件把「启用插件」开关放在最醒目的位置。
//
// 宿主契约（PluginConfigDialog）：
//   props:   initialConfig(已保存配置) / api / nativeSubscribe
//   emits:   save(config) 由宿主 PUT /plugin/<插件ID> 落盘并触发插件重载
//            close() 关闭弹窗；switch() 切到详情数据页（./Page）

// 字段默认值必须与后端 get_form() 的 defaults 保持一致，
// 首次配置（initialConfig 为空）时表单也能给出完整可用配置。
const DEFAULT_CONFIG = {
  enabled: true,
  rsshub_base_url: "http://127.0.0.1:1200",
  poll_interval: 30,
  max_entries: 50,
  max_notify_log: 200,
  fetch_full: true,
  proxy_images: true,
  mark_read_on_open: true,
  notify_enabled: true,
  opml_group: "导入",
  notify_template: "📰 [{feed}] {title}\n命中规则：{rule}\n{link}",
  notify_channel: "MessageCenter",
  webhook_url: "",
};

export default {
  name: "RsshubReaderConfig",
  props: {
    // 宿主注入：已持久化的插件配置
    initialConfig: { type: Object, default: () => ({}) },
    api: { type: Object, default: () => ({}) },
    nativeSubscribe: { type: Function, default: null },
  },
  // save：保存配置（宿主负责落盘）；close：关闭；switch：查看详情数据页
  emits: ["save", "close", "switch", "layout"],
  data() {
    return {
      // 合并默认值与已保存配置，避免新增字段缺失
      config: { ...DEFAULT_CONFIG, ...(this.initialConfig || {}) },
    };
  },
  computed: {
    // 数字字段统一以 number 提交，避免后端 int() 转换收到空字符串
    pollInterval: {
      get() {
        return this.config.poll_interval;
      },
      set(v) {
        this.config.poll_interval = Number(v) || 0;
      },
    },
    maxEntries: {
      get() {
        return this.config.max_entries;
      },
      set(v) {
        this.config.max_entries = Number(v) || 0;
      },
    },
    maxNotifyLog: {
      get() {
        return this.config.max_notify_log;
      },
      set(v) {
        this.config.max_notify_log = Number(v) || 0;
      },
    },
    // 通知渠道下拉项，与后端 get_form() VSelect 项一致
    channelItems() {
      return [
        { title: "MessageCenter（默认分发）", value: "MessageCenter" },
        { title: "Telegram", value: "Telegram" },
        { title: "飞书", value: "Feishu" },
        { title: "Slack", value: "Slack" },
        { title: "Discord", value: "Discord" },
        { title: "WebPush", value: "WebPush" },
        { title: "Webhook", value: "Webhook" },
      ];
    },
  },
  methods: {
    // 保存：交给宿主 PUT 落盘（宿主保存成功后会自动关闭/刷新并更新侧栏入口）
    handleSave() {
      this.$emit("save", { ...this.config });
    },
    // 通知宿主本组件期望的弹窗宽度（可选 layout 事件）
    emitLayout() {
      this.$emit("layout", { maxWidth: "56rem" });
    },
  },
  mounted() {
    this.emitLayout();
  },
};
</script>

<template>
  <div class="rsshub-config pa-4">
    <!-- 顶部标题 + 启用开关：MP v2 通过保存配置启用插件 -->
    <div class="d-flex align-center mb-3">
      <v-icon size="28" color="primary" class="mr-3">mdi-rss-box</v-icon>
      <div>
        <div class="text-h6">RSSHub 阅读器 · 设置</div>
        <div class="text-caption text-medium-emphasis">
          保存配置后生效；关闭开关并保存即停用插件
        </div>
      </div>
      <v-spacer />
      <v-switch
        v-model="config.enabled"
        color="success"
        density="compact"
        hide-details
        :label="config.enabled ? '已启用' : '已停用'"
        class="mt-2"
      />
    </div>

    <!-- 基础设置 -->
    <div class="text-subtitle-2 mb-1">基础设置</div>
    <v-row dense>
      <v-col cols="12" md="6">
        <v-text-field
          v-model="config.rsshub_base_url"
          label="RSSHub 地址"
          density="compact"
          hint="局域网 RSSHub 访问地址，如 http://192.168.1.100:1200"
          persistent-hint
        />
      </v-col>
      <v-col cols="6" md="3">
        <v-text-field
          v-model.number="pollInterval"
          label="刷新间隔（分钟）"
          type="number"
          density="compact"
          hint="建议 15~60，最小按 5 分钟执行"
          persistent-hint
        />
      </v-col>
      <v-col cols="6" md="3">
        <v-text-field
          v-model.number="maxEntries"
          label="每个源保留条数"
          type="number"
          density="compact"
        />
      </v-col>
      <v-col cols="6" md="3">
        <v-text-field
          v-model.number="maxNotifyLog"
          label="通知记录保留条数"
          type="number"
          density="compact"
        />
      </v-col>
      <v-col cols="6" md="3">
        <v-text-field
          v-model="config.opml_group"
          label="OPML 默认分组"
          density="compact"
          hint="OPML 导入未指定分组时使用"
          persistent-hint
        />
      </v-col>
    </v-row>

    <!-- 阅读与图片 -->
    <div class="text-subtitle-2 mt-2 mb-1">阅读与图片</div>
    <v-row dense>
      <v-col cols="12" md="4">
        <v-switch
          v-model="config.fetch_full"
          label="抓取正文提取完整图片"
          color="primary"
          density="compact"
          hide-details
        />
      </v-col>
      <v-col cols="12" md="4">
        <v-switch
          v-model="config.proxy_images"
          label="启用后端图片代理"
          color="primary"
          density="compact"
          hide-details
        />
      </v-col>
      <v-col cols="12" md="4">
        <v-switch
          v-model="config.mark_read_on_open"
          label="打开文章自动标为已读"
          color="primary"
          density="compact"
          hide-details
        />
      </v-col>
    </v-row>

    <!-- 规则通知 -->
    <div class="text-subtitle-2 mt-2 mb-1">规则通知</div>
    <v-row dense>
      <v-col cols="12" md="4">
        <v-switch
          v-model="config.notify_enabled"
          label="启用规则通知"
          color="primary"
          density="compact"
          hide-details
        />
      </v-col>
      <v-col cols="12" md="8">
        <v-select
          v-model="config.notify_channel"
          :items="channelItems"
          label="默认通知渠道"
          density="compact"
          hide-details
        />
      </v-col>
      <v-col cols="12" md="6">
        <v-textarea
          v-model="config.notify_template"
          label="通知内容模板"
          density="compact"
          rows="3"
          hint="支持变量：{title} {feed} {link} {rule} {published}"
          persistent-hint
        />
      </v-col>
      <v-col cols="12" md="6">
        <v-text-field
          v-model="config.webhook_url"
          label="Webhook 地址"
          density="compact"
          hint="渠道选择 Webhook 时，命中规则将 POST JSON 到此地址"
          persistent-hint
        />
      </v-col>
    </v-row>

    <!-- 底部操作：保存（启用/停用由上方开关决定）/ 查看数据 / 关闭 -->
    <div class="d-flex flex-wrap align-center mt-3">
      <v-btn color="primary" variant="flat" @click="handleSave">
        <v-icon start>mdi-content-save</v-icon>保存
      </v-btn>
      <v-btn class="ml-2" variant="outlined" @click="$emit('switch')">
        <v-icon start>mdi-database-eye-outline</v-icon>查看数据
      </v-btn>
      <v-spacer />
      <v-btn variant="text" @click="$emit('close')">关闭</v-btn>
    </div>
  </div>
</template>
