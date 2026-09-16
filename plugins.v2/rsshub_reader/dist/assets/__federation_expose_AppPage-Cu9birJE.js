import { importShared } from './__federation_fn_import-JrT3xvdd.js';

const _export_sfc = (sfc, props) => {
  const target = sfc.__vccOpts || sfc;
  for (const [key, val] of props) {
    target[key] = val;
  }
  return target;
};

// 兼容 MP 前端对插件 API 响应的两种形态：
// 1) 包装形态 {success: true, data: {...}} → 取 data；
// 2) 端点直接返回的 JSON {ok: true, ...} → 原样返回。
function unwrapResponse(res) {
  if (res && typeof res === "object" && "success" in res && "data" in res) {
    return res.data;
  }
  return res;
}

const _sfc_main = {
  name: "RsshubReaderAppPage",
  props: {
    // MP 主应用注入：插件 API 调用器 / 插件 ID / 侧边栏入口标识
    api: { type: Object, default: () => ({}) },
    pluginId: { type: String, default: "rsshub_reader" },
    navKey: { type: String, default: "main" },
  },
  data() {
    return {
      feeds: [],
      entries: [],
      selectedUrl: "",
      newUrl: "",
      newName: "",
      adding: false,
      refreshing: false,
      importing: false,
      errorMsg: "",
      infoMsg: "",
      dialog: false,
      current: {},
      previewDialog: false,
      previewUrl: "",
      useProxy: true,
      showUnreadOnly: false,
      importDialog: false,
      opmlFile: null,
      opmlGroup: "",

      // ---- 通知规则相关 ----
      currentTab: "feeds",
      rules: [],
      rulesLoading: false,
      notifyLog: [],
      ruleDialog: false,
      editingRule: this.emptyRule(),
      testResult: null,
    };
  },
  computed: {
    // 插件 API 基础路径（MP 统一挂载在 /api/v1/plugin/ 下）
    pluginBase() {
      return "plugin/" + (this.pluginId || "rsshub_reader");
    },
    currentFeedName() {
      const f = this.feeds.find((x) => x.url === this.selectedUrl);
      return f ? f.name : "";
    },
    totalUnread() {
      return this.feeds.reduce((sum, f) => sum + (f.unread || 0), 0);
    },
    visibleEntries() {
      if (!this.showUnreadOnly) return this.entries;
      return this.entries.filter((e) => !e.is_read);
    },
    // 正文富文本：开启图片代理时，把 <img src> 改写为代理地址，规避防盗链/跨域
    proxiedContent() {
      const html = this.current.content || "";
      if (!html || !this.useProxy) return html;
      return html.replace(
        /<img([^>]*?)\ssrc="(https?:[^"]+)"/gi,
        (m, attrs, src) => `<img${attrs} src="${this.imgUrl(src)}"`
      );
    },
    // 规则表格表头
    ruleHeaders() {
      return [
        { title: "启用", key: "enabled", width: 70 },
        { title: "规则名称", key: "name", sortable: true },
        { title: "匹配字段", key: "fields" },
        { title: "关键词", key: "keywords" },
        { title: "匹配方式", key: "match_type", width: 150 },
        { title: "渠道", key: "channel", width: 120 },
        { title: "最近命中", key: "last_hit", width: 160 },
        { title: "操作", key: "actions", width: 120, sortable: false },
      ];
    },
    // 匹配方式下拉项
    matchTypeItems() {
      return [
        { title: "关键词（不区分大小写）", value: "contains" },
        { title: "关键词（区分大小写）", value: "contains_case" },
        { title: "正则表达式", value: "regex" },
        { title: "精确匹配", value: "exact" },
      ];
    },
    // 通知渠道下拉项（与后端 _CHANNEL_MAP + Webhook 特殊分支保持一致）
    channelItems() {
      return [
        { title: "使用全局默认（MP 通知组件）", value: "" },
        { title: "MessageCenter（站内消息）", value: "MessageCenter" },
        { title: "Telegram", value: "Telegram" },
        { title: "飞书", value: "Feishu" },
        { title: "Slack", value: "Slack" },
        { title: "Discord", value: "Discord" },
        { title: "WebPush", value: "WebPush" },
        { title: "Webhook", value: "Webhook" },
      ];
    },
    // 匹配字段复选框项
    fieldOptions() {
      return [
        { title: "标题 (title)", value: "title" },
        { title: "描述 (description)", value: "description" },
        { title: "作者 (author)", value: "author" },
        { title: "分类 (category)", value: "category" },
        { title: "链接 (link)", value: "link" },
      ];
    },
    // 适用订阅源下拉项（含「全部」）
    feedUrlItems() {
      const list = [{ title: "全部源", value: "__all__" }];
      (this.feeds || []).forEach((f) => {
        list.push({ title: f.name || f.url, value: f.url });
      });
      return list;
    },
  },
  mounted() {
    this.loadFeeds();
    this.loadRules();
    this.loadNotifyLog();
  },
  methods: {
    // 图片代理直链（匿名可访问，供 <img> 直接加载）
    imgUrl(raw) {
      if (!raw) return "";
      if (!this.useProxy) return raw;
      return (
        "/api/v1/plugin/" +
        (this.pluginId || "rsshub_reader") +
        "/proxy?url=" +
        encodeURIComponent(raw)
      );
    },
    // 统一 API 调用：GET/DELETE 参数放 query，POST 放 body
    async call(path, { method = "GET", body } = {}) {
      try {
        let res;
        if (method === "POST") {
          res = await this.api.post(this.pluginBase + path, body || {});
        } else if (method === "DELETE") {
          res = await this.api.delete(this.pluginBase + path);
        } else {
          res = await this.api.get(this.pluginBase + path);
        }
        return unwrapResponse(res);
      } catch (e) {
        this.errorMsg = "请求失败：" + (e.message || e);
        return { ok: false };
      }
    },
    // 自动清除提示
    flash(msg, type = "error") {
      if (type === "error") this.errorMsg = msg;
      else this.infoMsg = msg;
      setTimeout(() => {
        this.errorMsg = "";
        this.infoMsg = "";
      }, 4000);
    },
    async loadFeeds() {
      const data = await this.call("/articles");
      if (data.ok) {
        this.feeds = data.feeds || [];
        if (this.feeds.length && !this.selectedUrl) {
          this.selectFeed(this.feeds[0].url);
        }
      }
    },
    async selectFeed(url) {
      this.selectedUrl = url;
      const data = await this.call("/articles?url=" + encodeURIComponent(url));
      if (data.ok) {
        this.entries = (data.data && data.data.entries) || [];
      }
    },
    async addFeed() {
      if (!this.newUrl.trim()) {
        this.flash("请输入 RSSHub 路由地址");
        return;
      }
      this.adding = true;
      try {
        const data = await this.call("/feeds", {
          method: "POST",
          body: { url: this.newUrl.trim(), name: this.newName.trim() },
        });
        if (data.ok) {
          this.feeds = data.feeds;
          this.newUrl = "";
          this.newName = "";
          this.selectFeed(this.feeds[this.feeds.length - 1].url);
          this.flash("添加成功", "info");
        } else {
          this.flash(data.msg);
        }
      } finally {
        this.adding = false;
      }
    },
    async deleteFeed(url) {
      if (!confirm("确定删除该订阅源？")) return;
      const data = await this.call("/feeds?url=" + encodeURIComponent(url), {
        method: "DELETE",
      });
      if (data.ok) {
        this.feeds = data.feeds;
        if (this.selectedUrl === url) {
          this.selectedUrl = "";
          this.entries = [];
        }
      }
    },
    async refreshAll() {
      this.refreshing = true;
      try {
        const data = await this.call("/refresh", { method: "POST" });
        if (data.ok) {
          if (this.selectedUrl) await this.selectFeed(this.selectedUrl);
          await this.loadFeeds();
          this.flash("刷新完成", "info");
        } else {
          this.flash(data.msg);
        }
      } finally {
        this.refreshing = false;
      }
    },
    // ---- 已读/未读 ----
    async toggleRead(art) {
      const wasRead = !!art.is_read;
      // 乐观更新
      art.is_read = !wasRead;
      this.$forceUpdate();
      const data = wasRead
        ? await this.call(
            "/read?feed_url=" +
              encodeURIComponent(this.selectedUrl) +
              "&entry_id=" +
              encodeURIComponent(art.id || art.link),
            { method: "DELETE" }
          )
        : await this.call("/read", {
            method: "POST",
            body: {
              feed_url: this.selectedUrl,
              entry_id: art.id || art.link,
              read: true,
            },
          });
      if (data.ok) {
        this.refreshFeedUnread(this.selectedUrl);
      } else {
        // 回滚
        art.is_read = wasRead;
        this.flash(data.msg || "操作失败");
      }
    },
    async markAllRead(feedUrl) {
      const data = await this.call("/read/all", {
        method: "POST",
        body: { feed_url: feedUrl },
      });
      if (data.ok) {
        this.flash(data.msg || "已全部标为已读", "info");
        await this.selectFeed(feedUrl);
        await this.loadFeeds();
      }
    },
    refreshFeedUnread(feedUrl) {
      // 本地重新拉取该源，更新左侧角标
      this.call("/articles?url=" + encodeURIComponent(feedUrl)).then((data) => {
        if (data.ok) {
          const unread = (data.data.entries || []).filter((e) => !e.is_read).length;
          const f = this.feeds.find((x) => x.url === feedUrl);
          if (f) f.unread = unread;
        }
      });
    },
    // ---- OPML 导出：后端返回 JSON {filename, content}，前端生成 Blob 下载 ----
    async downloadOpml() {
      const data = await this.call("/opml/export");
      if (data && data.ok && data.content) {
        const blob = new Blob([data.content], { type: "text/xml;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = data.filename || "rsshub_reader_subscriptions.opml";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        this.flash("OPML 已导出", "info");
      } else {
        this.flash((data && data.msg) || "导出失败");
      }
    },
    // ---- OPML 导入 ----
    async importOpml() {
      if (!this.opmlFile) return;
      this.importing = true;
      try {
        // 读取本地文件内容为字符串
        const text = await this.opmlFile.text();
        const data = await this.call("/opml/import", {
          method: "POST",
          body: { content: text, group: this.opmlGroup.trim() },
        });
        if (data.ok) {
          this.flash(
            `导入完成：成功 ${data.imported.length} 个，跳过 ${data.skipped.length} 个已存在`,
            "info"
          );
          this.importDialog = false;
          this.opmlFile = null;
          this.opmlGroup = "";
          await this.loadFeeds();
          if (this.feeds.length) this.selectFeed(this.feeds[0].url);
        } else {
          this.flash(data.msg);
        }
      } catch (e) {
        this.flash("导入失败：" + e.message);
      } finally {
        this.importing = false;
      }
    },
    // ---- 文章详情 ----
    openArticle(art) {
      this.current = { ...art };
      this.dialog = true;
      // 打开自动标为已读（可关闭：后台设置 mark_read_on_open）
      if (!art.is_read) {
        // 乐观更新
        art.is_read = true;
        this.$forceUpdate();
        this.call("/read", {
          method: "POST",
          body: {
            feed_url: this.selectedUrl,
            entry_id: art.id || art.link,
            read: true,
          },
        }).then((data) => {
          if (!data.ok) art.is_read = false; // 失败回滚
          else this.refreshFeedUnread(this.selectedUrl);
        });
      }
    },
    preview(i) {
      this.previewUrl = this.imgUrl(this.current.images[i]);
      this.previewDialog = true;
    },
    // 文章 key（id 可能为空，回退到 link + index）
    artKey(art, idx) {
      return art.id || art.link || idx;
    },

    // ================= 通知规则 =================
    emptyRule() {
      return {
        id: "",
        name: "",
        fields: ["title"],
        match_type: "contains",
        keywords: [],
        feed_urls: [],
        channel: "",
        enabled: true,
      };
    },
    async loadRules() {
      this.rulesLoading = true;
      try {
        const data = await this.call("/rules");
        if (data.ok) this.rules = data.rules || [];
      } finally {
        this.rulesLoading = false;
      }
    },
    async loadNotifyLog() {
      const data = await this.call("/notify/log");
      if (data.ok) this.notifyLog = data.log || [];
    },
    fieldLabel(f) {
      return (
        {
          title: "标题",
          description: "描述",
          author: "作者",
          category: "分类",
          link: "链接",
        }[f] || f
      );
    },
    matchTypeLabel(t) {
      return (
        {
          contains: "关键词（不区分大小写）",
          contains_case: "关键词（区分大小写）",
          regex: "正则表达式",
          exact: "精确匹配",
        }[t] || t
      );
    },
    openRuleDialog(rule) {
      this.testResult = null;
      if (rule) {
        // 深拷贝，避免编辑时直接改动列表
        this.editingRule = JSON.parse(JSON.stringify(rule));
        if (!Array.isArray(this.editingRule.fields)) this.editingRule.fields = ["title"];
        if (!Array.isArray(this.editingRule.keywords)) this.editingRule.keywords = [];
        if (!Array.isArray(this.editingRule.feed_urls)) this.editingRule.feed_urls = [];
      } else {
        this.editingRule = this.emptyRule();
      }
      this.ruleDialog = true;
    },
    async saveRule() {
      const payload = { ...this.editingRule };
      if (!payload.name || !payload.name.trim()) {
        this.flash("请输入规则名称");
        return;
      }
      if (!payload.fields || !payload.fields.length) {
        this.flash("请至少选择一个匹配字段");
        return;
      }
      if (!payload.keywords || !payload.keywords.length) {
        this.flash("请至少添加一个关键词");
        return;
      }
      // feed_urls 空 = 全部源，传 ["__all__"]
      if (!payload.feed_urls || !payload.feed_urls.length) {
        payload.feed_urls = ["__all__"];
      }
      const data = await this.call("/rules", {
        method: "POST",
        body: payload,
      });
      if (data.ok) {
        this.rules = data.rules || [];
        this.ruleDialog = false;
        this.flash("规则已保存", "info");
      } else {
        this.flash(data.msg || "保存失败");
      }
    },
    async toggleRule(rule, val) {
      // 复用 save：只改 enabled
      const updated = { ...rule, enabled: !!val };
      const data = await this.call("/rules", {
        method: "POST",
        body: updated,
      });
      if (data.ok) this.rules = data.rules || [];
    },
    async deleteRule(rule) {
      if (!confirm(`确定删除规则「${rule.name}」？`)) return;
      // 后端按 id 删除（query 参数）
      const data = await this.call("/rules?id=" + encodeURIComponent(rule.id), {
        method: "DELETE",
      });
      if (data.ok) {
        this.rules = data.rules || [];
        this.flash("已删除", "info");
      } else {
        this.flash(data.msg || "删除失败");
      }
    },
    async testCurrentRule() {
      // 试运行当前编辑中的规则（不发送通知）
      const payload = { ...this.editingRule };
      if (!payload.fields || !payload.fields.length) payload.fields = ["title"];
      if (!payload.keywords || !payload.keywords.length) {
        this.flash("请至少添加一个关键词");
        return;
      }
      if (!payload.feed_urls || !payload.feed_urls.length) payload.feed_urls = ["__all__"];
      const data = await this.call("/rules/test", {
        method: "POST",
        body: payload,
      });
      this.testResult = data;
    },
    async testRule(rule) {
      // 对已有规则试运行
      const data = await this.call("/rules/test", {
        method: "POST",
        body: rule,
      });
      this.testResult = data;
      this.flash(
        data.ok ? `试运行完成，命中 ${data.matched} 条（仅预览，未发送通知）` : data.msg,
        data.ok ? "info" : "error"
      );
    },
    async clearLog() {
      if (!confirm("确定清空全部通知记录？")) return;
      const data = await this.call("/notify/log", { method: "DELETE" });
      if (data.ok) {
        this.notifyLog = [];
        this.flash("已清空通知记录", "info");
      }
    },
  },
};

const {createTextVNode:_createTextVNode,resolveComponent:_resolveComponent,withCtx:_withCtx,createVNode:_createVNode,toDisplayString:_toDisplayString,openBlock:_openBlock,createBlock:_createBlock,createCommentVNode:_createCommentVNode,withKeys:_withKeys,mergeProps:_mergeProps,renderList:_renderList,Fragment:_Fragment,createElementBlock:_createElementBlock,withModifiers:_withModifiers,createElementVNode:_createElementVNode,normalizeClass:_normalizeClass,vShow:_vShow,withDirectives:_withDirectives} = await importShared('vue');


const _hoisted_1 = {
  key: 0,
  class: "text-primary"
};
const _hoisted_2 = { key: 1 };
const _hoisted_3 = { class: "d-flex align-center mb-2" };
const _hoisted_4 = { class: "text-subtitle-1" };
const _hoisted_5 = { class: "d-flex align-center justify-center fill-height" };
const _hoisted_6 = { class: "text-caption text-grey mb-2" };
const _hoisted_7 = { key: 0 };
const _hoisted_8 = { key: 1 };
const _hoisted_9 = {
  key: 0,
  class: "mb-4"
};
const _hoisted_10 = { class: "text-subtitle-2 mb-2" };
const _hoisted_11 = { class: "d-flex align-center justify-center fill-height" };
const _hoisted_12 = ["innerHTML"];
const _hoisted_13 = { class: "d-flex align-center justify-center fill-height" };
const _hoisted_14 = {
  key: 0,
  class: "mt-1 mb-0"
};
const _hoisted_15 = { class: "text-subtitle-1 font-weight-medium" };
const _hoisted_16 = {
  key: 0,
  class: "text-caption text-grey"
};
const _hoisted_17 = {
  key: 0,
  class: "text-caption"
};
const _hoisted_18 = {
  key: 1,
  class: "text-caption text-grey"
};
const _hoisted_19 = { class: "text-subtitle-1 font-weight-medium" };
const _hoisted_20 = { class: "text-caption text-grey" };

function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
  const _component_v_icon = _resolveComponent("v-icon");
  const _component_v_tab = _resolveComponent("v-tab");
  const _component_v_chip = _resolveComponent("v-chip");
  const _component_v_tabs = _resolveComponent("v-tabs");
  const _component_v_text_field = _resolveComponent("v-text-field");
  const _component_v_col = _resolveComponent("v-col");
  const _component_v_btn = _resolveComponent("v-btn");
  const _component_v_list_item_title = _resolveComponent("v-list-item-title");
  const _component_v_list_item = _resolveComponent("v-list-item");
  const _component_v_list = _resolveComponent("v-list");
  const _component_v_menu = _resolveComponent("v-menu");
  const _component_v_switch = _resolveComponent("v-switch");
  const _component_v_row = _resolveComponent("v-row");
  const _component_v_alert = _resolveComponent("v-alert");
  const _component_v_spacer = _resolveComponent("v-spacer");
  const _component_v_card_title = _resolveComponent("v-card-title");
  const _component_v_divider = _resolveComponent("v-divider");
  const _component_v_list_item_subtitle = _resolveComponent("v-list-item-subtitle");
  const _component_v_card = _resolveComponent("v-card");
  const _component_v_card_text = _resolveComponent("v-card-text");
  const _component_v_progress_circular = _resolveComponent("v-progress-circular");
  const _component_v_img = _resolveComponent("v-img");
  const _component_v_card_subtitle = _resolveComponent("v-card-subtitle");
  const _component_v_card_actions = _resolveComponent("v-card-actions");
  const _component_v_empty_state = _resolveComponent("v-empty-state");
  const _component_v_toolbar_title = _resolveComponent("v-toolbar-title");
  const _component_v_toolbar = _resolveComponent("v-toolbar");
  const _component_v_container = _resolveComponent("v-container");
  const _component_v_dialog = _resolveComponent("v-dialog");
  const _component_v_file_input = _resolveComponent("v-file-input");
  const _component_v_select = _resolveComponent("v-select");
  const _component_v_combobox = _resolveComponent("v-combobox");
  const _component_v_label = _resolveComponent("v-label");
  const _component_v_checkbox = _resolveComponent("v-checkbox");
  const _component_v_data_table = _resolveComponent("v-data-table");

  return (_openBlock(), _createBlock(_component_v_container, { fluid: "" }, {
    default: _withCtx(() => [
      _createVNode(_component_v_tabs, {
        modelValue: $data.currentTab,
        "onUpdate:modelValue": _cache[0] || (_cache[0] = $event => (($data.currentTab) = $event)),
        color: "primary",
        density: "comfortable",
        class: "mb-3"
      }, {
        default: _withCtx(() => [
          _createVNode(_component_v_tab, { value: "feeds" }, {
            default: _withCtx(() => [
              _createVNode(_component_v_icon, {
                start: "",
                size: "small"
              }, {
                default: _withCtx(() => [...(_cache[26] || (_cache[26] = [
                  _createTextVNode("mdi-rss", -1)
                ]))]),
                _: 1
              }),
              _cache[27] || (_cache[27] = _createTextVNode("订阅源 ", -1))
            ]),
            _: 1
          }),
          _createVNode(_component_v_tab, { value: "rules" }, {
            default: _withCtx(() => [
              _createVNode(_component_v_icon, {
                start: "",
                size: "small"
              }, {
                default: _withCtx(() => [...(_cache[28] || (_cache[28] = [
                  _createTextVNode("mdi-bell-outline", -1)
                ]))]),
                _: 1
              }),
              _cache[29] || (_cache[29] = _createTextVNode("通知规则 ", -1)),
              ($data.rules.length)
                ? (_openBlock(), _createBlock(_component_v_chip, {
                    key: 0,
                    size: "x-small",
                    class: "ml-2",
                    color: "primary",
                    variant: "tonal"
                  }, {
                    default: _withCtx(() => [
                      _createTextVNode(_toDisplayString($data.rules.length), 1)
                    ]),
                    _: 1
                  }))
                : _createCommentVNode("", true)
            ]),
            _: 1
          })
        ]),
        _: 1
      }, 8, ["modelValue"]),
      _withDirectives(_createElementVNode("div", null, [
        _createVNode(_component_v_row, {
          class: "mb-2",
          align: "center"
        }, {
          default: _withCtx(() => [
            _createVNode(_component_v_col, {
              cols: "12",
              md: "4"
            }, {
              default: _withCtx(() => [
                _createVNode(_component_v_text_field, {
                  modelValue: $data.newUrl,
                  "onUpdate:modelValue": _cache[1] || (_cache[1] = $event => (($data.newUrl) = $event)),
                  label: "RSSHub 路由地址",
                  placeholder: "如 /douban/movie/hot 的完整 RSS 地址",
                  density: "compact",
                  "hide-details": "",
                  onKeyup: _withKeys($options.addFeed, ["enter"])
                }, null, 8, ["modelValue", "onKeyup"])
              ]),
              _: 1
            }),
            _createVNode(_component_v_col, {
              cols: "12",
              md: "2"
            }, {
              default: _withCtx(() => [
                _createVNode(_component_v_text_field, {
                  modelValue: $data.newName,
                  "onUpdate:modelValue": _cache[2] || (_cache[2] = $event => (($data.newName) = $event)),
                  label: "备注名（可选）",
                  density: "compact",
                  "hide-details": ""
                }, null, 8, ["modelValue"])
              ]),
              _: 1
            }),
            _createVNode(_component_v_col, { cols: "auto" }, {
              default: _withCtx(() => [
                _createVNode(_component_v_btn, {
                  color: "primary",
                  loading: $data.adding,
                  onClick: $options.addFeed
                }, {
                  default: _withCtx(() => [...(_cache[30] || (_cache[30] = [
                    _createTextVNode("添加", -1)
                  ]))]),
                  _: 1
                }, 8, ["loading", "onClick"])
              ]),
              _: 1
            }),
            _createVNode(_component_v_col, { cols: "auto" }, {
              default: _withCtx(() => [
                _createVNode(_component_v_btn, {
                  variant: "outlined",
                  loading: $data.refreshing,
                  onClick: $options.refreshAll
                }, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_icon, { start: "" }, {
                      default: _withCtx(() => [...(_cache[31] || (_cache[31] = [
                        _createTextVNode("mdi-refresh", -1)
                      ]))]),
                      _: 1
                    }),
                    _cache[32] || (_cache[32] = _createTextVNode("刷新 ", -1))
                  ]),
                  _: 1
                }, 8, ["loading", "onClick"])
              ]),
              _: 1
            }),
            _createVNode(_component_v_col, { cols: "auto" }, {
              default: _withCtx(() => [
                _createVNode(_component_v_menu, null, {
                  activator: _withCtx(({ props }) => [
                    _createVNode(_component_v_btn, _mergeProps({ variant: "tonal" }, props), {
                      default: _withCtx(() => [
                        _createVNode(_component_v_icon, { start: "" }, {
                          default: _withCtx(() => [...(_cache[33] || (_cache[33] = [
                            _createTextVNode("mdi-import-export", -1)
                          ]))]),
                          _: 1
                        }),
                        _cache[34] || (_cache[34] = _createTextVNode("OPML ", -1))
                      ]),
                      _: 1
                    }, 16)
                  ]),
                  default: _withCtx(() => [
                    _createVNode(_component_v_list, { density: "compact" }, {
                      default: _withCtx(() => [
                        _createVNode(_component_v_list_item, { onClick: $options.downloadOpml }, {
                          default: _withCtx(() => [
                            _createVNode(_component_v_list_item_title, null, {
                              default: _withCtx(() => [
                                _createVNode(_component_v_icon, {
                                  start: "",
                                  size: "small"
                                }, {
                                  default: _withCtx(() => [...(_cache[35] || (_cache[35] = [
                                    _createTextVNode("mdi-export", -1)
                                  ]))]),
                                  _: 1
                                }),
                                _cache[36] || (_cache[36] = _createTextVNode("导出订阅源 ", -1))
                              ]),
                              _: 1
                            })
                          ]),
                          _: 1
                        }, 8, ["onClick"]),
                        _createVNode(_component_v_list_item, {
                          onClick: _cache[3] || (_cache[3] = $event => ($data.importDialog = true))
                        }, {
                          default: _withCtx(() => [
                            _createVNode(_component_v_list_item_title, null, {
                              default: _withCtx(() => [
                                _createVNode(_component_v_icon, {
                                  start: "",
                                  size: "small"
                                }, {
                                  default: _withCtx(() => [...(_cache[37] || (_cache[37] = [
                                    _createTextVNode("mdi-import", -1)
                                  ]))]),
                                  _: 1
                                }),
                                _cache[38] || (_cache[38] = _createTextVNode("导入 OPML ", -1))
                              ]),
                              _: 1
                            })
                          ]),
                          _: 1
                        })
                      ]),
                      _: 1
                    })
                  ]),
                  _: 1
                })
              ]),
              _: 1
            }),
            _createVNode(_component_v_col, { cols: "auto" }, {
              default: _withCtx(() => [
                _createVNode(_component_v_switch, {
                  modelValue: $data.useProxy,
                  "onUpdate:modelValue": _cache[4] || (_cache[4] = $event => (($data.useProxy) = $event)),
                  label: "图片代理",
                  density: "compact",
                  "hide-details": "",
                  color: "primary"
                }, null, 8, ["modelValue"])
              ]),
              _: 1
            }),
            _createVNode(_component_v_col, { cols: "auto" }, {
              default: _withCtx(() => [
                _createVNode(_component_v_switch, {
                  modelValue: $data.showUnreadOnly,
                  "onUpdate:modelValue": _cache[5] || (_cache[5] = $event => (($data.showUnreadOnly) = $event)),
                  label: "仅未读",
                  density: "compact",
                  "hide-details": "",
                  color: "primary"
                }, null, 8, ["modelValue"])
              ]),
              _: 1
            })
          ]),
          _: 1
        }),
        ($data.errorMsg)
          ? (_openBlock(), _createBlock(_component_v_row, { key: 0 }, {
              default: _withCtx(() => [
                _createVNode(_component_v_col, null, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_alert, {
                      type: "error",
                      variant: "tonal",
                      dense: ""
                    }, {
                      default: _withCtx(() => [
                        _createTextVNode(_toDisplayString($data.errorMsg), 1)
                      ]),
                      _: 1
                    })
                  ]),
                  _: 1
                })
              ]),
              _: 1
            }))
          : _createCommentVNode("", true),
        ($data.infoMsg)
          ? (_openBlock(), _createBlock(_component_v_row, { key: 1 }, {
              default: _withCtx(() => [
                _createVNode(_component_v_col, null, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_alert, {
                      type: "success",
                      variant: "tonal",
                      dense: ""
                    }, {
                      default: _withCtx(() => [
                        _createTextVNode(_toDisplayString($data.infoMsg), 1)
                      ]),
                      _: 1
                    })
                  ]),
                  _: 1
                })
              ]),
              _: 1
            }))
          : _createCommentVNode("", true),
        _createVNode(_component_v_row, null, {
          default: _withCtx(() => [
            _createVNode(_component_v_col, {
              cols: "12",
              md: "3"
            }, {
              default: _withCtx(() => [
                _createVNode(_component_v_card, null, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_card_title, { class: "text-subtitle-1 d-flex align-center" }, {
                      default: _withCtx(() => [
                        _cache[39] || (_cache[39] = _createTextVNode(" 订阅源 ", -1)),
                        _createVNode(_component_v_chip, {
                          size: "small",
                          class: "ml-2",
                          color: "primary",
                          variant: "tonal"
                        }, {
                          default: _withCtx(() => [
                            _createTextVNode(_toDisplayString($options.totalUnread), 1)
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_v_spacer),
                        ($data.selectedUrl)
                          ? (_openBlock(), _createBlock(_component_v_btn, {
                              key: 0,
                              icon: "mdi-check-all",
                              size: "x-small",
                              variant: "text",
                              title: "标记当前源全部已读",
                              onClick: _cache[6] || (_cache[6] = $event => ($options.markAllRead($data.selectedUrl)))
                            }))
                          : _createCommentVNode("", true)
                      ]),
                      _: 1
                    }),
                    _createVNode(_component_v_divider),
                    _createVNode(_component_v_list, {
                      lines: "two",
                      density: "compact"
                    }, {
                      default: _withCtx(() => [
                        (_openBlock(true), _createElementBlock(_Fragment, null, _renderList($data.feeds, (f) => {
                          return (_openBlock(), _createBlock(_component_v_list_item, {
                            key: f.url,
                            active: $data.selectedUrl === f.url,
                            onClick: $event => ($options.selectFeed(f.url))
                          }, {
                            append: _withCtx(() => [
                              _createVNode(_component_v_btn, {
                                icon: "mdi-delete",
                                size: "x-small",
                                variant: "text",
                                color: "error",
                                onClick: _withModifiers($event => ($options.deleteFeed(f.url)), ["stop"])
                              }, null, 8, ["onClick"])
                            ]),
                            default: _withCtx(() => [
                              _createVNode(_component_v_list_item_title, null, {
                                default: _withCtx(() => [
                                  _createTextVNode(_toDisplayString(f.name) + " ", 1),
                                  (f.unread > 0)
                                    ? (_openBlock(), _createBlock(_component_v_chip, {
                                        key: 0,
                                        size: "x-small",
                                        color: "error",
                                        variant: "flat",
                                        class: "ml-1"
                                      }, {
                                        default: _withCtx(() => [
                                          _createTextVNode(_toDisplayString(f.unread), 1)
                                        ]),
                                        _: 2
                                      }, 1024))
                                    : _createCommentVNode("", true)
                                ]),
                                _: 2
                              }, 1024),
                              _createVNode(_component_v_list_item_subtitle, null, {
                                default: _withCtx(() => [
                                  (f.group)
                                    ? (_openBlock(), _createElementBlock("span", _hoisted_1, _toDisplayString(f.group) + " · ", 1))
                                    : _createCommentVNode("", true),
                                  _createTextVNode(" " + _toDisplayString(f.title || '加载中...') + " · " + _toDisplayString(f.count || 0) + " 篇 ", 1)
                                ]),
                                _: 2
                              }, 1024)
                            ]),
                            _: 2
                          }, 1032, ["active", "onClick"]))
                        }), 128)),
                        (!$data.feeds.length)
                          ? (_openBlock(), _createBlock(_component_v_list_item, { key: 0 }, {
                              default: _withCtx(() => [
                                _createVNode(_component_v_list_item_title, { class: "text-grey" }, {
                                  default: _withCtx(() => [...(_cache[40] || (_cache[40] = [
                                    _createTextVNode(" 暂无订阅源，点 OPML → 导入 或从 RSSHub 添加 ", -1)
                                  ]))]),
                                  _: 1
                                })
                              ]),
                              _: 1
                            }))
                          : _createCommentVNode("", true)
                      ]),
                      _: 1
                    })
                  ]),
                  _: 1
                })
              ]),
              _: 1
            }),
            _createVNode(_component_v_col, {
              cols: "12",
              md: "9"
            }, {
              default: _withCtx(() => [
                (!$data.selectedUrl)
                  ? (_openBlock(), _createBlock(_component_v_card, { key: 0 }, {
                      default: _withCtx(() => [
                        _createVNode(_component_v_card_text, { class: "text-grey" }, {
                          default: _withCtx(() => [...(_cache[41] || (_cache[41] = [
                            _createTextVNode("请从左侧选择一个订阅源", -1)
                          ]))]),
                          _: 1
                        })
                      ]),
                      _: 1
                    }))
                  : (_openBlock(), _createElementBlock("div", _hoisted_2, [
                      _createElementVNode("div", _hoisted_3, [
                        _createElementVNode("span", _hoisted_4, _toDisplayString($options.currentFeedName), 1),
                        _createVNode(_component_v_spacer),
                        _createVNode(_component_v_btn, {
                          size: "small",
                          variant: "text",
                          "prepend-icon": "mdi-check-all",
                          onClick: _cache[7] || (_cache[7] = $event => ($options.markAllRead($data.selectedUrl)))
                        }, {
                          default: _withCtx(() => [...(_cache[42] || (_cache[42] = [
                            _createTextVNode(" 全部标为已读 ", -1)
                          ]))]),
                          _: 1
                        })
                      ]),
                      _createVNode(_component_v_row, null, {
                        default: _withCtx(() => [
                          (_openBlock(true), _createElementBlock(_Fragment, null, _renderList($options.visibleEntries, (art, idx) => {
                            return (_openBlock(), _createBlock(_component_v_col, {
                              key: $options.artKey(art, idx),
                              cols: "12",
                              sm: "6",
                              md: "4"
                            }, {
                              default: _withCtx(() => [
                                _createVNode(_component_v_card, {
                                  class: _normalizeClass(["h-100 entry-card", { 'is-read': art.is_read }]),
                                  hover: "",
                                  onClick: $event => ($options.openArticle(art))
                                }, {
                                  default: _withCtx(() => [
                                    (art.thumbnail)
                                      ? (_openBlock(), _createBlock(_component_v_img, {
                                          key: 0,
                                          src: $options.imgUrl(art.thumbnail),
                                          height: "140",
                                          cover: "",
                                          gradient: "to bottom, rgba(0,0,0,0) 60%, rgba(0,0,0,0.5)"
                                        }, {
                                          placeholder: _withCtx(() => [
                                            _createElementVNode("div", _hoisted_5, [
                                              _createVNode(_component_v_progress_circular, {
                                                indeterminate: "",
                                                size: "24"
                                              })
                                            ])
                                          ]),
                                          _: 1
                                        }, 8, ["src"]))
                                      : _createCommentVNode("", true),
                                    _createVNode(_component_v_card_title, { class: "text-subtitle-2 two-line" }, {
                                      default: _withCtx(() => [
                                        (!art.is_read)
                                          ? (_openBlock(), _createBlock(_component_v_icon, {
                                              key: 0,
                                              size: "x-small",
                                              color: "primary",
                                              class: "mr-1"
                                            }, {
                                              default: _withCtx(() => [...(_cache[43] || (_cache[43] = [
                                                _createTextVNode("mdi-circle-medium", -1)
                                              ]))]),
                                              _: 1
                                            }))
                                          : _createCommentVNode("", true),
                                        _createTextVNode(" " + _toDisplayString(art.title), 1)
                                      ]),
                                      _: 2
                                    }, 1024),
                                    (art.published)
                                      ? (_openBlock(), _createBlock(_component_v_card_subtitle, { key: 1 }, {
                                          default: _withCtx(() => [
                                            _createTextVNode(_toDisplayString(art.published), 1)
                                          ]),
                                          _: 2
                                        }, 1024))
                                      : _createCommentVNode("", true),
                                    _createVNode(_component_v_card_text, { class: "text-body-2 text-grey-darken-1 clamp-2" }, {
                                      default: _withCtx(() => [
                                        _createTextVNode(_toDisplayString(art.summary), 1)
                                      ]),
                                      _: 2
                                    }, 1024),
                                    _createVNode(_component_v_card_actions, null, {
                                      default: _withCtx(() => [
                                        (art.images && art.images.length)
                                          ? (_openBlock(), _createBlock(_component_v_chip, {
                                              key: 0,
                                              size: "small",
                                              color: "primary",
                                              variant: "tonal"
                                            }, {
                                              default: _withCtx(() => [
                                                _createVNode(_component_v_icon, {
                                                  start: "",
                                                  size: "x-small"
                                                }, {
                                                  default: _withCtx(() => [...(_cache[44] || (_cache[44] = [
                                                    _createTextVNode("mdi-image", -1)
                                                  ]))]),
                                                  _: 1
                                                }),
                                                _createTextVNode(" " + _toDisplayString(art.images.length), 1)
                                              ]),
                                              _: 2
                                            }, 1024))
                                          : _createCommentVNode("", true),
                                        _createVNode(_component_v_spacer),
                                        _createVNode(_component_v_btn, {
                                          icon: art.is_read ? 'mdi-email-open' : 'mdi-email',
                                          size: "x-small",
                                          variant: "text",
                                          title: art.is_read ? '标为未读' : '标为已读',
                                          onClick: _withModifiers($event => ($options.toggleRead(art)), ["stop"])
                                        }, null, 8, ["icon", "title", "onClick"]),
                                        _createVNode(_component_v_btn, {
                                          icon: "mdi-open-in-new",
                                          size: "x-small",
                                          variant: "text",
                                          href: art.link,
                                          target: "_blank",
                                          onClick: _cache[8] || (_cache[8] = _withModifiers(() => {}, ["stop"]))
                                        }, null, 8, ["href"])
                                      ]),
                                      _: 2
                                    }, 1024)
                                  ]),
                                  _: 2
                                }, 1032, ["class", "onClick"])
                              ]),
                              _: 2
                            }, 1024))
                          }), 128))
                        ]),
                        _: 1
                      }),
                      (!$options.visibleEntries.length)
                        ? (_openBlock(), _createBlock(_component_v_empty_state, {
                            key: 0,
                            icon: "mdi-rss-off",
                            title: $data.showUnreadOnly ? '没有未读文章 🎉' : '该源暂无文章',
                            text: "尝试点一下『刷新』"
                          }, null, 8, ["title"]))
                        : _createCommentVNode("", true)
                    ]))
              ]),
              _: 1
            })
          ]),
          _: 1
        }),
        _createVNode(_component_v_dialog, {
          modelValue: $data.dialog,
          "onUpdate:modelValue": _cache[11] || (_cache[11] = $event => (($data.dialog) = $event)),
          fullscreen: "",
          transition: "dialog-bottom-transition"
        }, {
          default: _withCtx(() => [
            _createVNode(_component_v_card, null, {
              default: _withCtx(() => [
                _createVNode(_component_v_toolbar, {
                  color: "primary",
                  density: "compact"
                }, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_btn, {
                      icon: "mdi-close",
                      onClick: _cache[9] || (_cache[9] = $event => ($data.dialog = false))
                    }),
                    _createVNode(_component_v_toolbar_title, null, {
                      default: _withCtx(() => [
                        _createTextVNode(_toDisplayString($data.current.title), 1)
                      ]),
                      _: 1
                    }),
                    _createVNode(_component_v_spacer),
                    _createVNode(_component_v_btn, {
                      "prepend-icon": $data.current.is_read ? 'mdi-email' : 'mdi-email-open',
                      variant: "text",
                      onClick: _cache[10] || (_cache[10] = $event => ($options.toggleRead($data.current)))
                    }, {
                      default: _withCtx(() => [
                        _createTextVNode(_toDisplayString($data.current.is_read ? '标为未读' : '标为已读'), 1)
                      ]),
                      _: 1
                    }, 8, ["prepend-icon"]),
                    ($data.current.link)
                      ? (_openBlock(), _createBlock(_component_v_btn, {
                          key: 0,
                          href: $data.current.link,
                          target: "_blank",
                          variant: "text"
                        }, {
                          default: _withCtx(() => [...(_cache[45] || (_cache[45] = [
                            _createTextVNode("原文", -1)
                          ]))]),
                          _: 1
                        }, 8, ["href"]))
                      : _createCommentVNode("", true)
                  ]),
                  _: 1
                }),
                _createVNode(_component_v_container, { fluid: "" }, {
                  default: _withCtx(() => [
                    _createElementVNode("div", _hoisted_6, [
                      ($data.current.author)
                        ? (_openBlock(), _createElementBlock("span", _hoisted_7, _toDisplayString($data.current.author) + " · ", 1))
                        : _createCommentVNode("", true),
                      ($data.current.published)
                        ? (_openBlock(), _createElementBlock("span", _hoisted_8, _toDisplayString($data.current.published), 1))
                        : _createCommentVNode("", true)
                    ]),
                    ($data.current.images && $data.current.images.length)
                      ? (_openBlock(), _createElementBlock("div", _hoisted_9, [
                          _createElementVNode("div", _hoisted_10, [
                            _createVNode(_component_v_icon, {
                              start: "",
                              size: "small"
                            }, {
                              default: _withCtx(() => [...(_cache[46] || (_cache[46] = [
                                _createTextVNode("mdi-image-multiple", -1)
                              ]))]),
                              _: 1
                            }),
                            _createTextVNode(" 图片 (" + _toDisplayString($data.current.images.length) + ") ", 1)
                          ]),
                          _createVNode(_component_v_row, null, {
                            default: _withCtx(() => [
                              (_openBlock(true), _createElementBlock(_Fragment, null, _renderList($data.current.images, (img, i) => {
                                return (_openBlock(), _createBlock(_component_v_col, {
                                  key: i,
                                  cols: "6",
                                  sm: "4",
                                  md: "3"
                                }, {
                                  default: _withCtx(() => [
                                    _createVNode(_component_v_img, {
                                      src: $options.imgUrl(img),
                                      "aspect-ratio": "1",
                                      cover: "",
                                      class: "rounded",
                                      onClick: $event => ($options.preview(i))
                                    }, {
                                      placeholder: _withCtx(() => [
                                        _createElementVNode("div", _hoisted_11, [
                                          _createVNode(_component_v_progress_circular, {
                                            indeterminate: "",
                                            size: "20"
                                          })
                                        ])
                                      ]),
                                      _: 1
                                    }, 8, ["src", "onClick"])
                                  ]),
                                  _: 2
                                }, 1024))
                              }), 128))
                            ]),
                            _: 1
                          })
                        ]))
                      : (_openBlock(), _createBlock(_component_v_alert, {
                          key: 1,
                          type: "info",
                          variant: "tonal",
                          density: "compact"
                        }, {
                          default: _withCtx(() => [...(_cache[47] || (_cache[47] = [
                            _createTextVNode(" 该文章未提取到图片 ", -1)
                          ]))]),
                          _: 1
                        })),
                    ($data.current.content)
                      ? (_openBlock(), _createElementBlock("div", {
                          key: 2,
                          class: "article-content",
                          innerHTML: $options.proxiedContent
                        }, null, 8, _hoisted_12))
                      : (_openBlock(), _createBlock(_component_v_alert, {
                          key: 3,
                          type: "warning",
                          variant: "tonal"
                        }, {
                          default: _withCtx(() => [...(_cache[48] || (_cache[48] = [
                            _createTextVNode(" 无正文内容（可开启『抓取正文』重新刷新） ", -1)
                          ]))]),
                          _: 1
                        }))
                  ]),
                  _: 1
                })
              ]),
              _: 1
            })
          ]),
          _: 1
        }, 8, ["modelValue"]),
        _createVNode(_component_v_dialog, {
          modelValue: $data.previewDialog,
          "onUpdate:modelValue": _cache[12] || (_cache[12] = $event => (($data.previewDialog) = $event)),
          "max-width": "900"
        }, {
          default: _withCtx(() => [
            _createVNode(_component_v_img, {
              src: $data.previewUrl,
              "max-height": "80vh",
              contain: ""
            }, {
              placeholder: _withCtx(() => [
                _createElementVNode("div", _hoisted_13, [
                  _createVNode(_component_v_progress_circular, { indeterminate: "" })
                ])
              ]),
              _: 1
            }, 8, ["src"])
          ]),
          _: 1
        }, 8, ["modelValue"]),
        _createVNode(_component_v_dialog, {
          modelValue: $data.importDialog,
          "onUpdate:modelValue": _cache[16] || (_cache[16] = $event => (($data.importDialog) = $event)),
          "max-width": "600"
        }, {
          default: _withCtx(() => [
            _createVNode(_component_v_card, null, {
              default: _withCtx(() => [
                _createVNode(_component_v_card_title, null, {
                  default: _withCtx(() => [...(_cache[49] || (_cache[49] = [
                    _createTextVNode("导入 OPML", -1)
                  ]))]),
                  _: 1
                }),
                _createVNode(_component_v_card_text, null, {
                  default: _withCtx(() => [
                    _cache[50] || (_cache[50] = _createElementVNode("p", { class: "text-caption text-grey" }, " 支持 Feedly / Inoreader / Miniflux / FreshRSS 等导出的 OPML 1.0/2.0。 已存在的源会自动跳过，不重复添加。 ", -1)),
                    _createVNode(_component_v_file_input, {
                      modelValue: $data.opmlFile,
                      "onUpdate:modelValue": _cache[13] || (_cache[13] = $event => (($data.opmlFile) = $event)),
                      label: "选择 .opml 文件",
                      accept: ".opml,.xml,text/xml",
                      density: "compact",
                      "prepend-icon": "mdi-file-upload"
                    }, null, 8, ["modelValue"]),
                    _createVNode(_component_v_text_field, {
                      modelValue: $data.opmlGroup,
                      "onUpdate:modelValue": _cache[14] || (_cache[14] = $event => (($data.opmlGroup) = $event)),
                      label: "分组（可选）",
                      placeholder: "留空则使用 OPML 内的文件夹结构",
                      density: "compact"
                    }, null, 8, ["modelValue"])
                  ]),
                  _: 1
                }),
                _createVNode(_component_v_card_actions, null, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_spacer),
                    _createVNode(_component_v_btn, {
                      variant: "text",
                      onClick: _cache[15] || (_cache[15] = $event => ($data.importDialog = false))
                    }, {
                      default: _withCtx(() => [...(_cache[51] || (_cache[51] = [
                        _createTextVNode("取消", -1)
                      ]))]),
                      _: 1
                    }),
                    _createVNode(_component_v_btn, {
                      color: "primary",
                      loading: $data.importing,
                      disabled: !$data.opmlFile,
                      onClick: $options.importOpml
                    }, {
                      default: _withCtx(() => [...(_cache[52] || (_cache[52] = [
                        _createTextVNode("导入", -1)
                      ]))]),
                      _: 1
                    }, 8, ["loading", "disabled", "onClick"])
                  ]),
                  _: 1
                })
              ]),
              _: 1
            })
          ]),
          _: 1
        }, 8, ["modelValue"]),
        _createVNode(_component_v_dialog, {
          modelValue: $data.ruleDialog,
          "onUpdate:modelValue": _cache[24] || (_cache[24] = $event => (($data.ruleDialog) = $event)),
          "max-width": "720",
          persistent: ""
        }, {
          default: _withCtx(() => [
            _createVNode(_component_v_card, null, {
              default: _withCtx(() => [
                _createVNode(_component_v_card_title, null, {
                  default: _withCtx(() => [
                    _createTextVNode(_toDisplayString($data.editingRule.id ? '编辑规则' : '新建规则'), 1)
                  ]),
                  _: 1
                }),
                _createVNode(_component_v_card_text, null, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_row, { dense: "" }, {
                      default: _withCtx(() => [
                        _createVNode(_component_v_col, { cols: "12" }, {
                          default: _withCtx(() => [
                            _createVNode(_component_v_text_field, {
                              modelValue: $data.editingRule.name,
                              "onUpdate:modelValue": _cache[17] || (_cache[17] = $event => (($data.editingRule.name) = $event)),
                              label: "规则名称",
                              placeholder: "例如：重要科技新闻",
                              density: "compact",
                              rules: [v => !!v.trim() || '规则名称不能为空']
                            }, null, 8, ["modelValue", "rules"])
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_v_col, {
                          cols: "12",
                          md: "6"
                        }, {
                          default: _withCtx(() => [
                            _createVNode(_component_v_select, {
                              modelValue: $data.editingRule.match_type,
                              "onUpdate:modelValue": _cache[18] || (_cache[18] = $event => (($data.editingRule.match_type) = $event)),
                              items: $options.matchTypeItems,
                              label: "匹配方式",
                              density: "compact"
                            }, null, 8, ["modelValue", "items"])
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_v_col, {
                          cols: "12",
                          md: "6"
                        }, {
                          default: _withCtx(() => [
                            _createVNode(_component_v_select, {
                              modelValue: $data.editingRule.channel,
                              "onUpdate:modelValue": _cache[19] || (_cache[19] = $event => (($data.editingRule.channel) = $event)),
                              items: $options.channelItems,
                              label: "通知渠道（留空用全局默认）",
                              density: "compact",
                              clearable: ""
                            }, null, 8, ["modelValue", "items"])
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_v_col, { cols: "12" }, {
                          default: _withCtx(() => [
                            _createVNode(_component_v_combobox, {
                              modelValue: $data.editingRule.keywords,
                              "onUpdate:modelValue": _cache[20] || (_cache[20] = $event => (($data.editingRule.keywords) = $event)),
                              label: "正向关键词（每行/每项一个，OR 逻辑）",
                              placeholder: "输入后回车添加，如 AI、GPT",
                              density: "compact",
                              multiple: "",
                              chips: "",
                              "closable-chips": ""
                            }, null, 8, ["modelValue"])
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_v_col, { cols: "12" }, {
                          default: _withCtx(() => [
                            _createVNode(_component_v_label, { class: "text-caption" }, {
                              default: _withCtx(() => [...(_cache[53] || (_cache[53] = [
                                _createTextVNode("匹配字段（可多选）", -1)
                              ]))]),
                              _: 1
                            }),
                            (_openBlock(true), _createElementBlock(_Fragment, null, _renderList($options.fieldOptions, (opt) => {
                              return (_openBlock(), _createBlock(_component_v_checkbox, {
                                key: opt.value,
                                modelValue: $data.editingRule.fields,
                                "onUpdate:modelValue": _cache[21] || (_cache[21] = $event => (($data.editingRule.fields) = $event)),
                                label: opt.title,
                                value: opt.value,
                                density: "compact",
                                "hide-details": "",
                                class: "mr-4 d-inline-flex"
                              }, null, 8, ["modelValue", "label", "value"]))
                            }), 128))
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_v_col, { cols: "12" }, {
                          default: _withCtx(() => [
                            _createVNode(_component_v_select, {
                              modelValue: $data.editingRule.feed_urls,
                              "onUpdate:modelValue": _cache[22] || (_cache[22] = $event => (($data.editingRule.feed_urls) = $event)),
                              items: $options.feedUrlItems,
                              label: "适用订阅源（留空 = 全部源）",
                              density: "compact",
                              multiple: "",
                              chips: "",
                              clearable: ""
                            }, null, 8, ["modelValue", "items"])
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_v_col, { cols: "12" }, {
                          default: _withCtx(() => [
                            ($data.testResult)
                              ? (_openBlock(), _createBlock(_component_v_alert, {
                                  key: 0,
                                  type: $data.testResult.ok ? 'success' : 'warning',
                                  variant: "tonal",
                                  density: "compact"
                                }, {
                                  default: _withCtx(() => [
                                    _createTextVNode(_toDisplayString($data.testResult.msg) + " ", 1),
                                    ($data.testResult.hits && $data.testResult.hits.length)
                                      ? (_openBlock(), _createElementBlock("ul", _hoisted_14, [
                                          (_openBlock(true), _createElementBlock(_Fragment, null, _renderList($data.testResult.hits.slice(0, 10), (h, i) => {
                                            return (_openBlock(), _createElementBlock("li", { key: i }, " [" + _toDisplayString(h.feed) + "] " + _toDisplayString(h.title), 1))
                                          }), 128))
                                        ]))
                                      : _createCommentVNode("", true)
                                  ]),
                                  _: 1
                                }, 8, ["type"]))
                              : _createCommentVNode("", true)
                          ]),
                          _: 1
                        })
                      ]),
                      _: 1
                    })
                  ]),
                  _: 1
                }),
                _createVNode(_component_v_card_actions, null, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_btn, {
                      variant: "text",
                      onClick: _cache[23] || (_cache[23] = $event => ($data.ruleDialog = false))
                    }, {
                      default: _withCtx(() => [...(_cache[54] || (_cache[54] = [
                        _createTextVNode("取消", -1)
                      ]))]),
                      _: 1
                    }),
                    _createVNode(_component_v_btn, {
                      variant: "tonal",
                      "prepend-icon": "mdi-play-circle-outline",
                      onClick: $options.testCurrentRule
                    }, {
                      default: _withCtx(() => [...(_cache[55] || (_cache[55] = [
                        _createTextVNode(" 试运行 ", -1)
                      ]))]),
                      _: 1
                    }, 8, ["onClick"]),
                    _createVNode(_component_v_spacer),
                    _createVNode(_component_v_btn, {
                      color: "primary",
                      onClick: $options.saveRule
                    }, {
                      default: _withCtx(() => [...(_cache[56] || (_cache[56] = [
                        _createTextVNode("保存", -1)
                      ]))]),
                      _: 1
                    }, 8, ["onClick"])
                  ]),
                  _: 1
                })
              ]),
              _: 1
            })
          ]),
          _: 1
        }, 8, ["modelValue"])
      ], 512), [
        [_vShow, $data.currentTab === 'feeds']
      ]),
      _withDirectives(_createElementVNode("div", null, [
        _createVNode(_component_v_row, {
          class: "mb-2",
          align: "center"
        }, {
          default: _withCtx(() => [
            _createVNode(_component_v_col, {
              cols: "12",
              md: "6"
            }, {
              default: _withCtx(() => [
                _createElementVNode("span", _hoisted_15, [
                  _createVNode(_component_v_icon, {
                    start: "",
                    color: "primary"
                  }, {
                    default: _withCtx(() => [...(_cache[57] || (_cache[57] = [
                      _createTextVNode("mdi-bell-outline", -1)
                    ]))]),
                    _: 1
                  }),
                  _cache[58] || (_cache[58] = _createTextVNode("通知规则 ", -1))
                ]),
                _cache[59] || (_cache[59] = _createElementVNode("span", { class: "text-caption text-grey ml-2" }, " 监控订阅内容，命中关键词即通过 MP 通知组件提醒你阅读 ", -1))
              ]),
              _: 1
            }),
            _createVNode(_component_v_col, { cols: "auto" }, {
              default: _withCtx(() => [
                _createVNode(_component_v_btn, {
                  color: "primary",
                  "prepend-icon": "mdi-plus",
                  onClick: _cache[25] || (_cache[25] = $event => ($options.openRuleDialog()))
                }, {
                  default: _withCtx(() => [...(_cache[60] || (_cache[60] = [
                    _createTextVNode(" 新建规则 ", -1)
                  ]))]),
                  _: 1
                })
              ]),
              _: 1
            })
          ]),
          _: 1
        }),
        _createVNode(_component_v_card, null, {
          default: _withCtx(() => [
            _createVNode(_component_v_data_table, {
              headers: $options.ruleHeaders,
              items: $data.rules,
              loading: $data.rulesLoading,
              density: "comfortable",
              "no-data-text": "还没有规则，点右上角「新建规则」开始配置",
              "item-value": "id",
              "hide-default-footer": "",
              "items-per-page": -1
            }, {
              "item.enabled": _withCtx(({ item }) => [
                _createVNode(_component_v_switch, {
                  "model-value": item.enabled,
                  density: "compact",
                  "hide-details": "",
                  color: "primary",
                  "onUpdate:modelValue": $event => ($options.toggleRule(item, $event))
                }, null, 8, ["model-value", "onUpdate:modelValue"])
              ]),
              "item.fields": _withCtx(({ item }) => [
                (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(item.fields, (f) => {
                  return (_openBlock(), _createBlock(_component_v_chip, {
                    key: f,
                    size: "x-small",
                    class: "mr-1",
                    variant: "tonal"
                  }, {
                    default: _withCtx(() => [
                      _createTextVNode(_toDisplayString($options.fieldLabel(f)), 1)
                    ]),
                    _: 2
                  }, 1024))
                }), 128))
              ]),
              "item.keywords": _withCtx(({ item }) => [
                (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(item.keywords.slice(0, 5), (k, i) => {
                  return (_openBlock(), _createBlock(_component_v_chip, {
                    key: i,
                    size: "x-small",
                    color: "primary",
                    variant: "tonal",
                    class: "mr-1"
                  }, {
                    default: _withCtx(() => [
                      _createTextVNode(_toDisplayString(k), 1)
                    ]),
                    _: 2
                  }, 1024))
                }), 128)),
                (item.keywords.length > 5)
                  ? (_openBlock(), _createElementBlock("span", _hoisted_16, " +" + _toDisplayString(item.keywords.length - 5), 1))
                  : _createCommentVNode("", true)
              ]),
              "item.match_type": _withCtx(({ item }) => [
                _createTextVNode(_toDisplayString($options.matchTypeLabel(item.match_type)), 1)
              ]),
              "item.channel": _withCtx(({ item }) => [
                _createTextVNode(_toDisplayString(item.channel || '默认'), 1)
              ]),
              "item.last_hit": _withCtx(({ item }) => [
                (item.last_hit)
                  ? (_openBlock(), _createElementBlock("span", _hoisted_17, _toDisplayString(item.last_hit), 1))
                  : (_openBlock(), _createElementBlock("span", _hoisted_18, "从未命中"))
              ]),
              "item.actions": _withCtx(({ item }) => [
                _createVNode(_component_v_btn, {
                  icon: "mdi-play-circle-outline",
                  size: "x-small",
                  variant: "text",
                  title: "试运行（不发送通知）",
                  onClick: $event => ($options.testRule(item))
                }, null, 8, ["onClick"]),
                _createVNode(_component_v_btn, {
                  icon: "mdi-pencil-outline",
                  size: "x-small",
                  variant: "text",
                  title: "编辑",
                  onClick: $event => ($options.openRuleDialog(item))
                }, null, 8, ["onClick"]),
                _createVNode(_component_v_btn, {
                  icon: "mdi-delete-outline",
                  size: "x-small",
                  variant: "text",
                  color: "error",
                  title: "删除",
                  onClick: $event => ($options.deleteRule(item))
                }, null, 8, ["onClick"])
              ]),
              _: 1
            }, 8, ["headers", "items", "loading"])
          ]),
          _: 1
        }),
        _createVNode(_component_v_row, {
          class: "mt-4",
          align: "center"
        }, {
          default: _withCtx(() => [
            _createVNode(_component_v_col, {
              cols: "12",
              md: "6"
            }, {
              default: _withCtx(() => [
                _createElementVNode("span", _hoisted_19, [
                  _createVNode(_component_v_icon, {
                    start: "",
                    color: "primary"
                  }, {
                    default: _withCtx(() => [...(_cache[61] || (_cache[61] = [
                      _createTextVNode("mdi-history", -1)
                    ]))]),
                    _: 1
                  }),
                  _cache[62] || (_cache[62] = _createTextVNode("最近通知记录 ", -1))
                ])
              ]),
              _: 1
            }),
            _createVNode(_component_v_col, { cols: "auto" }, {
              default: _withCtx(() => [
                _createVNode(_component_v_btn, {
                  variant: "text",
                  size: "small",
                  "prepend-icon": "mdi-delete-sweep-outline",
                  disabled: !$data.notifyLog.length,
                  onClick: $options.clearLog
                }, {
                  default: _withCtx(() => [...(_cache[63] || (_cache[63] = [
                    _createTextVNode("清空记录", -1)
                  ]))]),
                  _: 1
                }, 8, ["disabled", "onClick"])
              ]),
              _: 1
            })
          ]),
          _: 1
        }),
        _createVNode(_component_v_card, null, {
          default: _withCtx(() => [
            ($data.notifyLog.length)
              ? (_openBlock(), _createBlock(_component_v_list, {
                  key: 0,
                  lines: "two",
                  density: "compact"
                }, {
                  default: _withCtx(() => [
                    (_openBlock(true), _createElementBlock(_Fragment, null, _renderList($data.notifyLog, (log, i) => {
                      return (_openBlock(), _createBlock(_component_v_list_item, { key: i }, {
                        prepend: _withCtx(() => [
                          _createVNode(_component_v_icon, { color: "success" }, {
                            default: _withCtx(() => [...(_cache[64] || (_cache[64] = [
                              _createTextVNode("mdi-check-circle-outline", -1)
                            ]))]),
                            _: 1
                          })
                        ]),
                        append: _withCtx(() => [
                          _createElementVNode("span", _hoisted_20, _toDisplayString(log.at), 1)
                        ]),
                        default: _withCtx(() => [
                          _createVNode(_component_v_list_item_title, null, {
                            default: _withCtx(() => [
                              _createTextVNode(_toDisplayString(log.title), 1)
                            ]),
                            _: 2
                          }, 1024),
                          _createVNode(_component_v_list_item_subtitle, null, {
                            default: _withCtx(() => [
                              _cache[65] || (_cache[65] = _createTextVNode(" 来自 ", -1)),
                              _createElementVNode("b", null, _toDisplayString(log.feed), 1),
                              _createTextVNode(" · 命中规则「" + _toDisplayString(log.rule) + "」· 渠道 " + _toDisplayString(log.channel), 1)
                            ]),
                            _: 2
                          }, 1024)
                        ]),
                        _: 2
                      }, 1024))
                    }), 128))
                  ]),
                  _: 1
                }))
              : (_openBlock(), _createBlock(_component_v_alert, {
                  key: 1,
                  type: "info",
                  variant: "tonal",
                  density: "compact"
                }, {
                  default: _withCtx(() => [...(_cache[66] || (_cache[66] = [
                    _createTextVNode(" 暂无通知记录。命中规则的文章会在这里出现，并同步到 MP 通知组件。 ", -1)
                  ]))]),
                  _: 1
                }))
          ]),
          _: 1
        }),
        _createVNode(_component_v_alert, {
          type: "info",
          variant: "tonal",
          density: "compact",
          class: "mt-4",
          icon: "mdi-information-outline"
        }, {
          default: _withCtx(() => [...(_cache[67] || (_cache[67] = [
            _createElementVNode("b", null, "规则行为：", -1),
            _createTextVNode(" 每次刷新订阅源时，仅对", -1),
            _createElementVNode("b", null, "首次出现", -1),
            _createTextVNode("的新条目匹配；已读条目不通知； 命中后", -1),
            _createElementVNode("b", null, "逐条即时", -1),
            _createTextVNode("发送并自动标为已读，去重不重复打扰。 ", -1)
          ]))]),
          _: 1
        })
      ], 512), [
        [_vShow, $data.currentTab === 'rules']
      ])
    ]),
    _: 1
  }))
}
const AppPage = /*#__PURE__*/_export_sfc(_sfc_main, [['render',_sfc_render],['__scopeId',"data-v-bc9a8600"]]);

export { AppPage as default };
