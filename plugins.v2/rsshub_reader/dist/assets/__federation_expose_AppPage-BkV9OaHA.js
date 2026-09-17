import { importShared } from './__federation_fn_import-JrT3xvdd.js';
import { _ as _export_sfc } from './_plugin-vue_export-helper-pcqpp-6-.js';

const _sfc_main$1 = {
  name: "RsshubFeedList",
  props: {
    // 订阅源列表（含 name/group/title/count/unread 字段）
    feeds: { type: Array, default: () => [] },
    // 当前选中的订阅源地址
    selectedUrl: { type: String, default: "" },
    // 未读总数
    totalUnread: { type: Number, default: 0 },
  },
  emits: ["select", "delete", "mark-all-read"],
};

const {toDisplayString:_toDisplayString$1,createTextVNode:_createTextVNode$1,resolveComponent:_resolveComponent$1,withCtx:_withCtx$1,createVNode:_createVNode$1,openBlock:_openBlock$1,createBlock:_createBlock$1,createCommentVNode:_createCommentVNode$1,renderList:_renderList$1,Fragment:_Fragment$1,createElementBlock:_createElementBlock$1,withModifiers:_withModifiers$1} = await importShared('vue');


const _hoisted_1$1 = {
  key: 0,
  class: "text-primary"
};

function _sfc_render$1(_ctx, _cache, $props, $setup, $data, $options) {
  const _component_v_chip = _resolveComponent$1("v-chip");
  const _component_v_spacer = _resolveComponent$1("v-spacer");
  const _component_v_btn = _resolveComponent$1("v-btn");
  const _component_v_card_title = _resolveComponent$1("v-card-title");
  const _component_v_divider = _resolveComponent$1("v-divider");
  const _component_v_list_item_title = _resolveComponent$1("v-list-item-title");
  const _component_v_list_item_subtitle = _resolveComponent$1("v-list-item-subtitle");
  const _component_v_list_item = _resolveComponent$1("v-list-item");
  const _component_v_list = _resolveComponent$1("v-list");
  const _component_v_card = _resolveComponent$1("v-card");

  return (_openBlock$1(), _createBlock$1(_component_v_card, { class: "h-100 d-flex flex-column" }, {
    default: _withCtx$1(() => [
      _createVNode$1(_component_v_card_title, { class: "text-subtitle-1 d-flex align-center" }, {
        default: _withCtx$1(() => [
          _cache[1] || (_cache[1] = _createTextVNode$1(" 订阅源 ", -1)),
          _createVNode$1(_component_v_chip, {
            size: "small",
            class: "ml-2",
            color: "primary",
            variant: "tonal"
          }, {
            default: _withCtx$1(() => [
              _createTextVNode$1(_toDisplayString$1($props.totalUnread), 1)
            ]),
            _: 1
          }),
          _createVNode$1(_component_v_spacer),
          ($props.selectedUrl)
            ? (_openBlock$1(), _createBlock$1(_component_v_btn, {
                key: 0,
                icon: "mdi-check-all",
                size: "small",
                variant: "text",
                title: "标记当前源全部已读",
                "aria-label": "标记当前源全部已读",
                onClick: _cache[0] || (_cache[0] = $event => (_ctx.$emit('mark-all-read', $props.selectedUrl)))
              }))
            : _createCommentVNode$1("", true)
        ]),
        _: 1
      }),
      _createVNode$1(_component_v_divider),
      _createVNode$1(_component_v_list, {
        lines: "two",
        density: "comfortable",
        class: "flex-grow-1 overflow-y-auto"
      }, {
        default: _withCtx$1(() => [
          (_openBlock$1(true), _createElementBlock$1(_Fragment$1, null, _renderList$1($props.feeds, (f) => {
            return (_openBlock$1(), _createBlock$1(_component_v_list_item, {
              key: f.url,
              active: $props.selectedUrl === f.url,
              class: "feed-item",
              onClick: $event => (_ctx.$emit('select', f.url))
            }, {
              append: _withCtx$1(() => [
                _createVNode$1(_component_v_btn, {
                  icon: "mdi-delete",
                  size: "small",
                  variant: "text",
                  color: "error",
                  title: "删除该订阅源",
                  "aria-label": "删除该订阅源",
                  onClick: _withModifiers$1($event => (_ctx.$emit('delete', f.url)), ["stop"])
                }, null, 8, ["onClick"])
              ]),
              default: _withCtx$1(() => [
                _createVNode$1(_component_v_list_item_title, null, {
                  default: _withCtx$1(() => [
                    _createTextVNode$1(_toDisplayString$1(f.name) + " ", 1),
                    (f.unread > 0)
                      ? (_openBlock$1(), _createBlock$1(_component_v_chip, {
                          key: 0,
                          size: "x-small",
                          color: "error",
                          variant: "flat",
                          class: "ml-1"
                        }, {
                          default: _withCtx$1(() => [
                            _createTextVNode$1(_toDisplayString$1(f.unread), 1)
                          ]),
                          _: 2
                        }, 1024))
                      : _createCommentVNode$1("", true)
                  ]),
                  _: 2
                }, 1024),
                _createVNode$1(_component_v_list_item_subtitle, null, {
                  default: _withCtx$1(() => [
                    (f.group)
                      ? (_openBlock$1(), _createElementBlock$1("span", _hoisted_1$1, _toDisplayString$1(f.group) + " · ", 1))
                      : _createCommentVNode$1("", true),
                    _createTextVNode$1(" " + _toDisplayString$1(f.title || '加载中...') + " · " + _toDisplayString$1(f.count || 0) + " 篇 ", 1)
                  ]),
                  _: 2
                }, 1024)
              ]),
              _: 2
            }, 1032, ["active", "onClick"]))
          }), 128)),
          (!$props.feeds.length)
            ? (_openBlock$1(), _createBlock$1(_component_v_list_item, { key: 0 }, {
                default: _withCtx$1(() => [
                  _createVNode$1(_component_v_list_item_title, { class: "text-grey" }, {
                    default: _withCtx$1(() => [...(_cache[2] || (_cache[2] = [
                      _createTextVNode$1(" 暂无订阅源，点 OPML → 导入 或从 RSSHub 添加 ", -1)
                    ]))]),
                    _: 1
                  })
                ]),
                _: 1
              }))
            : _createCommentVNode$1("", true)
        ]),
        _: 1
      })
    ]),
    _: 1
  }))
}
const RsshubFeedList = /*#__PURE__*/_export_sfc(_sfc_main$1, [['render',_sfc_render$1],['__scopeId',"data-v-11836c69"]]);

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
  components: { RsshubFeedList },
  props: {
    // MP 主应用注入：插件 API 调用器 / 插件 ID / 侧边栏入口标识
    // 注意：MP 插件 ID 为后端「类名」RsshubReader（非目录名），缺省值必须与其一致
    api: { type: Object, default: () => ({}) },
    pluginId: { type: String, default: "RsshubReader" },
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
      // 移动端：订阅源抽屉开关 + 单栏视图（'list' 文章列表 / 'content' 正文）
      drawer: false,
      mobilePane: "list",
      importing: false,
      errorMsg: "",
      infoMsg: "",
      current: {},
      contentLoading: false, // 正在按需抓取原文正文
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
      testing: false, // 通知测试进行中（防止连点重复发送）
      savingRule: false, // 规则保存中（防止连点生成重复规则）
      flashTimer: null, // 提示自动清除计时器（组件卸载时清理）
    };
  },
  computed: {
    // 是否移动端（<960px）：驱动订阅源抽屉与「文章列表 / 正文」单栏切换
    isMobile() {
      return this.$vuetify.display.smAndDown;
    },
    // 插件 API 基础路径（MP 统一挂载在 /api/v1/plugin/ 下）
    pluginBase() {
      return "plugin/" + (this.pluginId || "RsshubReader");
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
    // v-file-input 在 Vuetify 3 中 v-model 绑定的是 File 数组（即使未开 multiple），
    // 这里统一归一成单个 File，避免直接调用数组的 .text() 报错
    opmlFileObj() {
      const f = this.opmlFile;
      if (!f) return null;
      return Array.isArray(f) ? f[0] || null : f;
    },
  },
  watch: {
    // 切到桌面端时关闭抽屉：否则抽屉与常驻左栏会同时出现两份订阅源列表
    isMobile(mobile) {
      if (!mobile) this.drawer = false;
    },
  },
  mounted() {
    this.loadFeeds();
    this.loadRules();
    this.loadNotifyLog();
  },
  unmounted() {
    // 清理提示计时器，避免组件卸载后回调仍访问已销毁实例
    if (this.flashTimer) {
      clearTimeout(this.flashTimer);
      this.flashTimer = null;
    }
  },
  methods: {
    // 图片代理直链（匿名可访问，供 <img> 直接加载）
    imgUrl(raw) {
      if (!raw) return "";
      if (!this.useProxy) return raw;
      return (
        "/api/v1/plugin/" +
        (this.pluginId || "RsshubReader") +
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
    // 自动清除提示：用独立计时器，避免上一条的定时器把新提示提前清掉
    flash(msg, type = "error") {
      if (type === "error") this.errorMsg = msg;
      else this.infoMsg = msg;
      if (this.flashTimer) clearTimeout(this.flashTimer);
      this.flashTimer = setTimeout(() => {
        this.errorMsg = "";
        this.infoMsg = "";
        this.flashTimer = null;
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
    // 从抽屉选择订阅源后自动收起抽屉（仅移动端会用到）
    onDrawerSelect(url) {
      this.drawer = false;
      this.selectFeed(url);
    },
    async selectFeed(url) {
      this.selectedUrl = url;
      // 切换订阅源时先清空右栏与文章列表，避免请求返回前仍显示上一个源的文章
      this.current = {};
      this.entries = [];
      // 移动端切源后回到文章列表：否则中栏被 v-show 隐藏，只剩右栏空态、列表不可达
      if (this.isMobile) this.mobilePane = "list";
      const data = await this.call("/articles?url=" + encodeURIComponent(url));
      // 请求返回时用户可能已切到别的源，丢弃过期响应，避免列表与当前源不匹配
      if (this.selectedUrl !== url) return;
      if (data.ok) {
        this.entries = (data.data && data.data.entries) || [];
      } else {
        this.flash(data.msg || "文章加载失败");
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
          // 同步清空右栏并回到列表：避免继续显示已删除源的文章
          this.current = {};
          if (this.isMobile) this.mobilePane = "list";
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
      const file = this.opmlFileObj;
      // 未选择文件时直接返回（按钮已置灰，此处再兜底一次）
      if (!file) return;
      this.importing = true;
      try {
        // 读取本地文件内容为字符串
        const text = await file.text();
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
    // ---- 文章详情（右栏内联展示）----
    openArticle(art) {
      this.current = { ...art };
      // 移动端切到正文单栏；桌面端两栏并排，无需切换
      if (this.isMobile) this.mobilePane = "content";
      // 先按需补齐正文（RSS 通常只给摘要），再处理已读标记
      this.loadFullContent(art);
      // 打开自动标为已读（可关闭：后台设置 mark_read_on_open）
      if (!art.is_read) {
        // 乐观更新：列表项与右栏当前文章必须同步，否则右栏按钮文案与实际已读状态相反
        art.is_read = true;
        this.current.is_read = true;
        this.$forceUpdate();
        this.call("/read", {
          method: "POST",
          body: {
            feed_url: this.selectedUrl,
            entry_id: art.id || art.link,
            read: true,
          },
        }).then((data) => {
          if (!data.ok) {
            // 失败一起回滚
            art.is_read = false;
            this.current.is_read = false;
          } else {
            this.refreshFeedUnread(this.selectedUrl);
          }
        });
      }
    },
    // 按需抓取完整正文：RSS 里的正文常为摘要（纯文本过短），此时请求后端抓原网页；
    // 抓取结果由后端回写缓存，同一篇再次打开直接命中，不会重复请求。
    async loadFullContent(art) {
      // 统一交给后端判断是否需要抓取（命中有效缓存时后端立即返回），
      // 前端不再按文本长度自行跳过——否则正文提取算法升级后仍会沿用旧缓存
      if (!art.link) return;
      this.contentLoading = true;
      try {
        const data = await this.call(
          "/article/content?feed_url=" +
            encodeURIComponent(this.selectedUrl) +
            "&entry_id=" +
            encodeURIComponent(art.id || art.link)
        );
        // 请求期间用户可能已切到别的文章或订阅源，丢弃过期响应，避免右栏串内容/串图
        if (this.current.link !== art.link) return;
        if (data.ok) {
          this.current.content = data.content;
          // 正文抓取后图片以正文内为准，同步到右栏与中栏列表（含“已无图”的清空场景），
          // 避免继续展示 RSS/整页带进来的站点 logo、横幅等装饰图
          const images = data.images || [];
          this.current.images = images;
          art.images = images;
          art.thumbnail = images.length ? images[0] : "";
        } else {
          this.flash(data.msg || "正文抓取失败");
        }
      } finally {
        this.contentLoading = false;
      }
    },
    // 关闭右栏内容，回到未选中状态
    closeArticle() {
      this.current = {};
      // 移动端必须回到文章列表：否则停在正文栏且内容为空，列表不可达
      if (this.isMobile) this.mobilePane = "list";
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
      // 防连点：保存期间置 loading，避免重复提交生成重复规则
      this.savingRule = true;
      try {
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
      } finally {
        this.savingRule = false;
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
    // 通知测试：真实走一遍消息通知流程（后端最多发送前 3 条样例），
    // 用于验证通知渠道是否配置正确；不写去重记录、不标记已读，不污染正式流程
    async testCurrentRule() {
      // 试运行当前编辑中的规则，notify=true 才会真正发送通知
      const payload = { ...this.editingRule, notify: true };
      if (!payload.fields || !payload.fields.length) payload.fields = ["title"];
      if (!payload.keywords || !payload.keywords.length) {
        this.flash("请至少添加一个关键词");
        return;
      }
      if (!payload.feed_urls || !payload.feed_urls.length) payload.feed_urls = ["__all__"];
      this.testing = true;
      try {
        const data = await this.call("/rules/test", {
          method: "POST",
          body: payload,
        });
        this.testResult = data;
        if (!data.ok) this.flash(data.msg || "通知测试失败");
      } finally {
        this.testing = false;
      }
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

const {createTextVNode:_createTextVNode,resolveComponent:_resolveComponent,withCtx:_withCtx,createVNode:_createVNode,toDisplayString:_toDisplayString,openBlock:_openBlock,createBlock:_createBlock,createCommentVNode:_createCommentVNode,withKeys:_withKeys,mergeProps:_mergeProps,createElementVNode:_createElementVNode,renderList:_renderList,Fragment:_Fragment,createElementBlock:_createElementBlock,withModifiers:_withModifiers,normalizeClass:_normalizeClass,vShow:_vShow,withDirectives:_withDirectives} = await importShared('vue');


const _hoisted_1 = { class: "text-caption text-medium-emphasis mt-1" };
const _hoisted_2 = { key: 1 };
const _hoisted_3 = { class: "d-flex align-center mb-2" };
const _hoisted_4 = { class: "text-subtitle-1 text-truncate mr-2" };
const _hoisted_5 = { class: "d-flex align-start" };
const _hoisted_6 = { class: "d-flex align-center justify-center fill-height" };
const _hoisted_7 = { class: "flex-grow-1 min-w-0" };
const _hoisted_8 = { class: "text-subtitle-1" };
const _hoisted_9 = { class: "text-caption text-medium-emphasis mt-1" };
const _hoisted_10 = { class: "d-flex justify-center flex-wrap mt-4" };
const _hoisted_11 = {
  key: 0,
  class: "pt-2 pl-2"
};
const _hoisted_12 = { key: 0 };
const _hoisted_13 = { key: 1 };
const _hoisted_14 = {
  key: 0,
  class: "mb-4"
};
const _hoisted_15 = { class: "text-subtitle-2 mb-2" };
const _hoisted_16 = { class: "d-flex align-center justify-center fill-height" };
const _hoisted_17 = {
  key: 2,
  class: "d-flex align-center text-medium-emphasis my-4"
};
const _hoisted_18 = ["innerHTML"];
const _hoisted_19 = { class: "d-flex align-center justify-center fill-height" };
const _hoisted_20 = {
  key: 0,
  class: "mt-1 mb-0"
};
const _hoisted_21 = { class: "text-subtitle-1 font-weight-medium" };
const _hoisted_22 = {
  key: 0,
  class: "text-caption text-grey"
};
const _hoisted_23 = {
  key: 0,
  class: "text-caption"
};
const _hoisted_24 = {
  key: 1,
  class: "text-caption text-grey"
};
const _hoisted_25 = { class: "text-subtitle-1 font-weight-medium" };
const _hoisted_26 = { class: "text-caption text-grey" };

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
  const _component_v_divider = _resolveComponent("v-divider");
  const _component_v_row = _resolveComponent("v-row");
  const _component_v_alert = _resolveComponent("v-alert");
  const _component_RsshubFeedList = _resolveComponent("RsshubFeedList");
  const _component_v_navigation_drawer = _resolveComponent("v-navigation-drawer");
  const _component_v_card = _resolveComponent("v-card");
  const _component_v_spacer = _resolveComponent("v-spacer");
  const _component_v_progress_circular = _resolveComponent("v-progress-circular");
  const _component_v_img = _resolveComponent("v-img");
  const _component_v_card_title = _resolveComponent("v-card-title");
  const _component_v_card_subtitle = _resolveComponent("v-card-subtitle");
  const _component_v_card_text = _resolveComponent("v-card-text");
  const _component_v_card_actions = _resolveComponent("v-card-actions");
  const _component_v_dialog = _resolveComponent("v-dialog");
  const _component_v_file_input = _resolveComponent("v-file-input");
  const _component_v_select = _resolveComponent("v-select");
  const _component_v_combobox = _resolveComponent("v-combobox");
  const _component_v_label = _resolveComponent("v-label");
  const _component_v_checkbox = _resolveComponent("v-checkbox");
  const _component_v_data_table = _resolveComponent("v-data-table");
  const _component_v_list_item_subtitle = _resolveComponent("v-list-item-subtitle");
  const _component_v_container = _resolveComponent("v-container");

  return (_openBlock(), _createBlock(_component_v_container, {
    fluid: "",
    class: "app-page"
  }, {
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
                default: _withCtx(() => [...(_cache[30] || (_cache[30] = [
                  _createTextVNode("mdi-rss", -1)
                ]))]),
                _: 1
              }),
              _cache[31] || (_cache[31] = _createTextVNode("订阅源 ", -1))
            ]),
            _: 1
          }),
          _createVNode(_component_v_tab, { value: "rules" }, {
            default: _withCtx(() => [
              _createVNode(_component_v_icon, {
                start: "",
                size: "small"
              }, {
                default: _withCtx(() => [...(_cache[32] || (_cache[32] = [
                  _createTextVNode("mdi-bell-outline", -1)
                ]))]),
                _: 1
              }),
              _cache[33] || (_cache[33] = _createTextVNode("通知规则 ", -1)),
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
              sm: "8",
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
            (!$options.isMobile)
              ? (_openBlock(), _createBlock(_component_v_col, {
                  key: 0,
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
                }))
              : _createCommentVNode("", true),
            _createVNode(_component_v_col, { cols: "auto" }, {
              default: _withCtx(() => [
                _createVNode(_component_v_btn, {
                  color: "primary",
                  loading: $data.adding,
                  onClick: $options.addFeed
                }, {
                  default: _withCtx(() => [...(_cache[34] || (_cache[34] = [
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
                      default: _withCtx(() => [...(_cache[35] || (_cache[35] = [
                        _createTextVNode("mdi-refresh", -1)
                      ]))]),
                      _: 1
                    }),
                    _cache[36] || (_cache[36] = _createTextVNode("刷新 ", -1))
                  ]),
                  _: 1
                }, 8, ["loading", "onClick"])
              ]),
              _: 1
            }),
            (!$options.isMobile)
              ? (_openBlock(), _createBlock(_component_v_col, {
                  key: 1,
                  cols: "auto"
                }, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_menu, null, {
                      activator: _withCtx(({ props }) => [
                        _createVNode(_component_v_btn, _mergeProps({ variant: "tonal" }, props), {
                          default: _withCtx(() => [
                            _createVNode(_component_v_icon, { start: "" }, {
                              default: _withCtx(() => [...(_cache[37] || (_cache[37] = [
                                _createTextVNode("mdi-import-export", -1)
                              ]))]),
                              _: 1
                            }),
                            _cache[38] || (_cache[38] = _createTextVNode("OPML ", -1))
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
                                      default: _withCtx(() => [...(_cache[39] || (_cache[39] = [
                                        _createTextVNode("mdi-export", -1)
                                      ]))]),
                                      _: 1
                                    }),
                                    _cache[40] || (_cache[40] = _createTextVNode("导出订阅源 ", -1))
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
                                      default: _withCtx(() => [...(_cache[41] || (_cache[41] = [
                                        _createTextVNode("mdi-import", -1)
                                      ]))]),
                                      _: 1
                                    }),
                                    _cache[42] || (_cache[42] = _createTextVNode("导入 OPML ", -1))
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
                }))
              : _createCommentVNode("", true),
            (!$options.isMobile)
              ? (_openBlock(), _createBlock(_component_v_col, {
                  key: 2,
                  cols: "auto"
                }, {
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
                }))
              : _createCommentVNode("", true),
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
            }),
            ($options.isMobile)
              ? (_openBlock(), _createBlock(_component_v_col, {
                  key: 3,
                  cols: "auto"
                }, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_menu, { location: "bottom end" }, {
                      activator: _withCtx(({ props }) => [
                        _createVNode(_component_v_btn, _mergeProps({
                          icon: "mdi-dots-vertical",
                          variant: "text"
                        }, props, {
                          title: "更多操作",
                          "aria-label": "更多操作"
                        }), null, 16)
                      ]),
                      default: _withCtx(() => [
                        _createVNode(_component_v_list, { density: "comfortable" }, {
                          default: _withCtx(() => [
                            _createVNode(_component_v_list_item, { onClick: $options.downloadOpml }, {
                              default: _withCtx(() => [
                                _createVNode(_component_v_list_item_title, null, {
                                  default: _withCtx(() => [
                                    _createVNode(_component_v_icon, {
                                      start: "",
                                      size: "small"
                                    }, {
                                      default: _withCtx(() => [...(_cache[43] || (_cache[43] = [
                                        _createTextVNode("mdi-export", -1)
                                      ]))]),
                                      _: 1
                                    }),
                                    _cache[44] || (_cache[44] = _createTextVNode("导出订阅源 ", -1))
                                  ]),
                                  _: 1
                                })
                              ]),
                              _: 1
                            }, 8, ["onClick"]),
                            _createVNode(_component_v_list_item, {
                              onClick: _cache[6] || (_cache[6] = $event => ($data.importDialog = true))
                            }, {
                              default: _withCtx(() => [
                                _createVNode(_component_v_list_item_title, null, {
                                  default: _withCtx(() => [
                                    _createVNode(_component_v_icon, {
                                      start: "",
                                      size: "small"
                                    }, {
                                      default: _withCtx(() => [...(_cache[45] || (_cache[45] = [
                                        _createTextVNode("mdi-import", -1)
                                      ]))]),
                                      _: 1
                                    }),
                                    _cache[46] || (_cache[46] = _createTextVNode("导入 OPML ", -1))
                                  ]),
                                  _: 1
                                })
                              ]),
                              _: 1
                            }),
                            _createVNode(_component_v_divider, { class: "my-1" }),
                            _createVNode(_component_v_list_item, null, {
                              default: _withCtx(() => [
                                _createVNode(_component_v_switch, {
                                  modelValue: $data.useProxy,
                                  "onUpdate:modelValue": _cache[7] || (_cache[7] = $event => (($data.useProxy) = $event)),
                                  label: "图片代理",
                                  density: "compact",
                                  "hide-details": "",
                                  color: "primary",
                                  class: "mt-1"
                                }, null, 8, ["modelValue"])
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
                }))
              : _createCommentVNode("", true)
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
                      density: "compact"
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
                      density: "compact"
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
        _createVNode(_component_v_navigation_drawer, {
          modelValue: $data.drawer,
          "onUpdate:modelValue": _cache[8] || (_cache[8] = $event => (($data.drawer) = $event)),
          temporary: "",
          location: "left",
          width: "290"
        }, {
          default: _withCtx(() => [
            _createVNode(_component_RsshubFeedList, {
              feeds: $data.feeds,
              "selected-url": $data.selectedUrl,
              "total-unread": $options.totalUnread,
              onSelect: $options.onDrawerSelect,
              onDelete: $options.deleteFeed,
              onMarkAllRead: $options.markAllRead
            }, null, 8, ["feeds", "selected-url", "total-unread", "onSelect", "onDelete", "onMarkAllRead"])
          ]),
          _: 1
        }, 8, ["modelValue"]),
        _createVNode(_component_v_row, null, {
          default: _withCtx(() => [
            (!$options.isMobile)
              ? (_openBlock(), _createBlock(_component_v_col, {
                  key: 0,
                  cols: "12",
                  md: "3"
                }, {
                  default: _withCtx(() => [
                    _createVNode(_component_RsshubFeedList, {
                      feeds: $data.feeds,
                      "selected-url": $data.selectedUrl,
                      "total-unread": $options.totalUnread,
                      onSelect: $options.selectFeed,
                      onDelete: $options.deleteFeed,
                      onMarkAllRead: $options.markAllRead
                    }, null, 8, ["feeds", "selected-url", "total-unread", "onSelect", "onDelete", "onMarkAllRead"])
                  ]),
                  _: 1
                }))
              : _createCommentVNode("", true),
            _withDirectives(_createVNode(_component_v_col, {
              cols: "12",
              md: "4"
            }, {
              default: _withCtx(() => [
                (!$data.selectedUrl)
                  ? (_openBlock(), _createBlock(_component_v_card, {
                      key: 0,
                      class: "text-center py-10 px-4"
                    }, {
                      default: _withCtx(() => [
                        _createVNode(_component_v_icon, {
                          size: "64",
                          color: "grey-lighten-1",
                          class: "mb-3"
                        }, {
                          default: _withCtx(() => [...(_cache[47] || (_cache[47] = [
                            _createTextVNode("mdi-rss", -1)
                          ]))]),
                          _: 1
                        }),
                        _cache[49] || (_cache[49] = _createElementVNode("div", { class: "text-subtitle-1" }, "请选择一个订阅源", -1)),
                        _createElementVNode("div", _hoisted_1, _toDisplayString($options.isMobile
              ? '点下方按钮选择订阅源，或用上方输入框添加新的 RSS 地址'
              : '从左侧列表点选，或用上方输入框添加新的 RSS 地址'), 1),
                        ($options.isMobile)
                          ? (_openBlock(), _createBlock(_component_v_btn, {
                              key: 0,
                              class: "mt-4",
                              variant: "tonal",
                              color: "primary",
                              "prepend-icon": "mdi-menu",
                              onClick: _cache[9] || (_cache[9] = $event => ($data.drawer = true))
                            }, {
                              default: _withCtx(() => [...(_cache[48] || (_cache[48] = [
                                _createTextVNode("选择订阅源", -1)
                              ]))]),
                              _: 1
                            }))
                          : _createCommentVNode("", true)
                      ]),
                      _: 1
                    }))
                  : (_openBlock(), _createElementBlock("div", _hoisted_2, [
                      _createElementVNode("div", _hoisted_3, [
                        ($options.isMobile)
                          ? (_openBlock(), _createBlock(_component_v_btn, {
                              key: 0,
                              icon: "mdi-menu",
                              size: "small",
                              variant: "text",
                              class: "mr-1",
                              title: "选择订阅源",
                              "aria-label": "选择订阅源",
                              onClick: _cache[10] || (_cache[10] = $event => ($data.drawer = true))
                            }))
                          : _createCommentVNode("", true),
                        _createElementVNode("span", _hoisted_4, _toDisplayString($options.currentFeedName), 1),
                        _createVNode(_component_v_spacer),
                        _createVNode(_component_v_btn, {
                          size: "small",
                          variant: "text",
                          "prepend-icon": "mdi-check-all",
                          onClick: _cache[11] || (_cache[11] = $event => ($options.markAllRead($data.selectedUrl)))
                        }, {
                          default: _withCtx(() => [...(_cache[50] || (_cache[50] = [
                            _createTextVNode(" 全部标为已读 ", -1)
                          ]))]),
                          _: 1
                        })
                      ]),
                      _createVNode(_component_v_row, { class: "entry-list" }, {
                        default: _withCtx(() => [
                          (_openBlock(true), _createElementBlock(_Fragment, null, _renderList($options.visibleEntries, (art, idx) => {
                            return (_openBlock(), _createBlock(_component_v_col, {
                              key: $options.artKey(art, idx),
                              cols: "12"
                            }, {
                              default: _withCtx(() => [
                                _createVNode(_component_v_card, {
                                  class: _normalizeClass(["entry-card mb-3", {
                  'is-read': art.is_read,
                  'is-active': art.link && art.link === $data.current.link,
                }]),
                                  hover: "",
                                  onClick: $event => ($options.openArticle(art))
                                }, {
                                  default: _withCtx(() => [
                                    _createElementVNode("div", _hoisted_5, [
                                      (art.thumbnail)
                                        ? (_openBlock(), _createBlock(_component_v_img, {
                                            key: 0,
                                            src: $options.imgUrl(art.thumbnail),
                                            width: $options.isMobile ? 64 : 56,
                                            height: $options.isMobile ? 64 : 56,
                                            cover: "",
                                            class: "entry-thumb",
                                            loading: "lazy",
                                            decoding: "async"
                                          }, {
                                            placeholder: _withCtx(() => [
                                              _createElementVNode("div", _hoisted_6, [
                                                _createVNode(_component_v_progress_circular, {
                                                  indeterminate: "",
                                                  size: "16"
                                                })
                                              ])
                                            ]),
                                            _: 1
                                          }, 8, ["src", "width", "height"]))
                                        : _createCommentVNode("", true),
                                      _createElementVNode("div", _hoisted_7, [
                                        _createVNode(_component_v_card_title, { class: "text-subtitle-2 two-line" }, {
                                          default: _withCtx(() => [
                                            (!art.is_read)
                                              ? (_openBlock(), _createBlock(_component_v_icon, {
                                                  key: 0,
                                                  size: "x-small",
                                                  color: "primary",
                                                  class: "mr-1"
                                                }, {
                                                  default: _withCtx(() => [...(_cache[51] || (_cache[51] = [
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
                                          ? (_openBlock(), _createBlock(_component_v_card_subtitle, { key: 0 }, {
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
                                        }, 1024)
                                      ])
                                    ]),
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
                                                  default: _withCtx(() => [...(_cache[52] || (_cache[52] = [
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
                                          onClick: _cache[12] || (_cache[12] = _withModifiers(() => {}, ["stop"]))
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
                        ? (_openBlock(), _createBlock(_component_v_card, {
                            key: 0,
                            class: "text-center py-10 px-4"
                          }, {
                            default: _withCtx(() => [
                              _createVNode(_component_v_icon, {
                                size: "64",
                                color: "grey-lighten-1",
                                class: "mb-3"
                              }, {
                                default: _withCtx(() => [
                                  _createTextVNode(_toDisplayString($data.showUnreadOnly ? 'mdi-email-check-outline' : 'mdi-rss-off'), 1)
                                ]),
                                _: 1
                              }),
                              _createElementVNode("div", _hoisted_8, _toDisplayString($data.showUnreadOnly ? '没有未读文章' : '该源暂无文章'), 1),
                              _createElementVNode("div", _hoisted_9, _toDisplayString($data.showUnreadOnly
                ? '当前已过滤已读文章，关闭「仅未读」即可查看全部'
                : '可能是刚添加的源或该源本身内容为空，点「刷新」重新拉取'), 1),
                              _createElementVNode("div", _hoisted_10, [
                                ($data.showUnreadOnly)
                                  ? (_openBlock(), _createBlock(_component_v_btn, {
                                      key: 0,
                                      class: "ma-1",
                                      variant: "tonal",
                                      "prepend-icon": "mdi-filter-off-outline",
                                      onClick: _cache[13] || (_cache[13] = $event => ($data.showUnreadOnly = false))
                                    }, {
                                      default: _withCtx(() => [...(_cache[53] || (_cache[53] = [
                                        _createTextVNode("查看全部", -1)
                                      ]))]),
                                      _: 1
                                    }))
                                  : _createCommentVNode("", true),
                                _createVNode(_component_v_btn, {
                                  class: "ma-1",
                                  variant: "tonal",
                                  color: "primary",
                                  "prepend-icon": "mdi-refresh",
                                  loading: $data.refreshing,
                                  onClick: $options.refreshAll
                                }, {
                                  default: _withCtx(() => [...(_cache[54] || (_cache[54] = [
                                    _createTextVNode("刷新", -1)
                                  ]))]),
                                  _: 1
                                }, 8, ["loading", "onClick"])
                              ])
                            ]),
                            _: 1
                          }))
                        : _createCommentVNode("", true)
                    ]))
              ]),
              _: 1
            }, 512), [
              [_vShow, !$options.isMobile || $data.mobilePane === 'list']
            ]),
            _withDirectives(_createVNode(_component_v_col, {
              cols: "12",
              md: "5"
            }, {
              default: _withCtx(() => [
                _createVNode(_component_v_card, { ref: "contentPane" }, {
                  default: _withCtx(() => [
                    ($options.isMobile)
                      ? (_openBlock(), _createElementBlock("div", _hoisted_11, [
                          _createVNode(_component_v_btn, {
                            variant: "text",
                            "prepend-icon": "mdi-arrow-left",
                            onClick: _cache[14] || (_cache[14] = $event => ($data.mobilePane = 'list'))
                          }, {
                            default: _withCtx(() => [...(_cache[55] || (_cache[55] = [
                              _createTextVNode("返回列表", -1)
                            ]))]),
                            _: 1
                          })
                        ]))
                      : _createCommentVNode("", true),
                    ($data.current.title)
                      ? (_openBlock(), _createElementBlock(_Fragment, { key: 1 }, [
                          _createVNode(_component_v_card_title, { class: "text-subtitle-1" }, {
                            default: _withCtx(() => [
                              _createTextVNode(_toDisplayString($data.current.title), 1)
                            ]),
                            _: 1
                          }),
                          _createVNode(_component_v_card_subtitle, { class: "pb-1" }, {
                            default: _withCtx(() => [
                              ($data.current.author)
                                ? (_openBlock(), _createElementBlock("span", _hoisted_12, _toDisplayString($data.current.author) + " · ", 1))
                                : _createCommentVNode("", true),
                              ($data.current.published)
                                ? (_openBlock(), _createElementBlock("span", _hoisted_13, _toDisplayString($data.current.published), 1))
                                : _createCommentVNode("", true)
                            ]),
                            _: 1
                          }),
                          _createVNode(_component_v_card_actions, { class: "pt-1" }, {
                            default: _withCtx(() => [
                              _createVNode(_component_v_btn, {
                                size: "small",
                                variant: "text",
                                "prepend-icon": $data.current.is_read ? 'mdi-email' : 'mdi-email-open',
                                onClick: _cache[15] || (_cache[15] = $event => ($options.toggleRead($data.current)))
                              }, {
                                default: _withCtx(() => [
                                  _createTextVNode(_toDisplayString($data.current.is_read ? '标为未读' : '标为已读'), 1)
                                ]),
                                _: 1
                              }, 8, ["prepend-icon"]),
                              ($data.current.link)
                                ? (_openBlock(), _createBlock(_component_v_btn, {
                                    key: 0,
                                    size: "small",
                                    variant: "text",
                                    "prepend-icon": "mdi-open-in-new",
                                    href: $data.current.link,
                                    target: "_blank"
                                  }, {
                                    default: _withCtx(() => [...(_cache[56] || (_cache[56] = [
                                      _createTextVNode("原文", -1)
                                    ]))]),
                                    _: 1
                                  }, 8, ["href"]))
                                : _createCommentVNode("", true),
                              _createVNode(_component_v_spacer),
                              _createVNode(_component_v_btn, {
                                size: "small",
                                variant: "text",
                                "prepend-icon": "mdi-close",
                                onClick: $options.closeArticle
                              }, {
                                default: _withCtx(() => [...(_cache[57] || (_cache[57] = [
                                  _createTextVNode("关闭", -1)
                                ]))]),
                                _: 1
                              }, 8, ["onClick"])
                            ]),
                            _: 1
                          }),
                          _createVNode(_component_v_divider),
                          _createVNode(_component_v_card_text, null, {
                            default: _withCtx(() => [
                              ($data.current.images && $data.current.images.length)
                                ? (_openBlock(), _createElementBlock("div", _hoisted_14, [
                                    _createElementVNode("div", _hoisted_15, [
                                      _createVNode(_component_v_icon, {
                                        start: "",
                                        size: "small"
                                      }, {
                                        default: _withCtx(() => [...(_cache[58] || (_cache[58] = [
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
                                            sm: "4"
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
                                                  _createElementVNode("div", _hoisted_16, [
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
                                : (!$data.contentLoading)
                                  ? (_openBlock(), _createBlock(_component_v_alert, {
                                      key: 1,
                                      type: "info",
                                      variant: "tonal",
                                      density: "compact"
                                    }, {
                                      default: _withCtx(() => [...(_cache[59] || (_cache[59] = [
                                        _createTextVNode(" 该文章未提取到图片 ", -1)
                                      ]))]),
                                      _: 1
                                    }))
                                  : _createCommentVNode("", true),
                              ($data.contentLoading)
                                ? (_openBlock(), _createElementBlock("div", _hoisted_17, [
                                    _createVNode(_component_v_progress_circular, {
                                      indeterminate: "",
                                      size: "20",
                                      class: "mr-2"
                                    }),
                                    _cache[60] || (_cache[60] = _createTextVNode(" 正在抓取原文正文… ", -1))
                                  ]))
                                : ($data.current.content)
                                  ? (_openBlock(), _createElementBlock("div", {
                                      key: 3,
                                      class: "article-content",
                                      innerHTML: $options.proxiedContent
                                    }, null, 8, _hoisted_18))
                                  : (_openBlock(), _createBlock(_component_v_alert, {
                                      key: 4,
                                      type: "warning",
                                      variant: "tonal"
                                    }, {
                                      default: _withCtx(() => [...(_cache[61] || (_cache[61] = [
                                        _createTextVNode(" 无正文内容（可在插件设置中开启『抓取正文提取完整图片』后刷新） ", -1)
                                      ]))]),
                                      _: 1
                                    }))
                            ]),
                            _: 1
                          })
                        ], 64))
                      : (_openBlock(), _createBlock(_component_v_card_text, {
                          key: 2,
                          class: "text-center text-grey py-12"
                        }, {
                          default: _withCtx(() => [
                            _createVNode(_component_v_icon, {
                              size: "56",
                              class: "mb-3"
                            }, {
                              default: _withCtx(() => [...(_cache[62] || (_cache[62] = [
                                _createTextVNode("mdi-book-open-page-variant-outline", -1)
                              ]))]),
                              _: 1
                            }),
                            _cache[63] || (_cache[63] = _createElementVNode("div", null, "请在中间选择一篇文章", -1))
                          ]),
                          _: 1
                        }))
                  ]),
                  _: 1
                }, 512)
              ]),
              _: 1
            }, 512), [
              [_vShow, !$options.isMobile || $data.mobilePane === 'content']
            ])
          ]),
          _: 1
        }),
        _createVNode(_component_v_dialog, {
          modelValue: $data.previewDialog,
          "onUpdate:modelValue": _cache[16] || (_cache[16] = $event => (($data.previewDialog) = $event)),
          "max-width": "900"
        }, {
          default: _withCtx(() => [
            _createVNode(_component_v_img, {
              src: $data.previewUrl,
              "max-height": "80vh",
              contain: ""
            }, {
              placeholder: _withCtx(() => [
                _createElementVNode("div", _hoisted_19, [
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
          "onUpdate:modelValue": _cache[20] || (_cache[20] = $event => (($data.importDialog) = $event)),
          "max-width": "600"
        }, {
          default: _withCtx(() => [
            _createVNode(_component_v_card, null, {
              default: _withCtx(() => [
                _createVNode(_component_v_card_title, null, {
                  default: _withCtx(() => [...(_cache[64] || (_cache[64] = [
                    _createTextVNode("导入 OPML", -1)
                  ]))]),
                  _: 1
                }),
                _createVNode(_component_v_card_text, null, {
                  default: _withCtx(() => [
                    _cache[65] || (_cache[65] = _createElementVNode("p", { class: "text-caption text-grey" }, " 支持 Feedly / Inoreader / Miniflux / FreshRSS 等导出的 OPML 1.0/2.0。 已存在的源会自动跳过，不重复添加。 ", -1)),
                    _createVNode(_component_v_file_input, {
                      modelValue: $data.opmlFile,
                      "onUpdate:modelValue": _cache[17] || (_cache[17] = $event => (($data.opmlFile) = $event)),
                      label: "选择 .opml 文件",
                      accept: ".opml,.xml,text/xml",
                      density: "compact",
                      "prepend-icon": "mdi-file-upload"
                    }, null, 8, ["modelValue"]),
                    _createVNode(_component_v_text_field, {
                      modelValue: $data.opmlGroup,
                      "onUpdate:modelValue": _cache[18] || (_cache[18] = $event => (($data.opmlGroup) = $event)),
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
                      onClick: _cache[19] || (_cache[19] = $event => ($data.importDialog = false))
                    }, {
                      default: _withCtx(() => [...(_cache[66] || (_cache[66] = [
                        _createTextVNode("取消", -1)
                      ]))]),
                      _: 1
                    }),
                    _createVNode(_component_v_btn, {
                      color: "primary",
                      loading: $data.importing,
                      disabled: !$options.opmlFileObj,
                      onClick: $options.importOpml
                    }, {
                      default: _withCtx(() => [...(_cache[67] || (_cache[67] = [
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
          "onUpdate:modelValue": _cache[28] || (_cache[28] = $event => (($data.ruleDialog) = $event)),
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
                              "onUpdate:modelValue": _cache[21] || (_cache[21] = $event => (($data.editingRule.name) = $event)),
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
                              "onUpdate:modelValue": _cache[22] || (_cache[22] = $event => (($data.editingRule.match_type) = $event)),
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
                              "onUpdate:modelValue": _cache[23] || (_cache[23] = $event => (($data.editingRule.channel) = $event)),
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
                              "onUpdate:modelValue": _cache[24] || (_cache[24] = $event => (($data.editingRule.keywords) = $event)),
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
                              default: _withCtx(() => [...(_cache[68] || (_cache[68] = [
                                _createTextVNode("匹配字段（可多选）", -1)
                              ]))]),
                              _: 1
                            }),
                            (_openBlock(true), _createElementBlock(_Fragment, null, _renderList($options.fieldOptions, (opt) => {
                              return (_openBlock(), _createBlock(_component_v_checkbox, {
                                key: opt.value,
                                modelValue: $data.editingRule.fields,
                                "onUpdate:modelValue": _cache[25] || (_cache[25] = $event => (($data.editingRule.fields) = $event)),
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
                              "onUpdate:modelValue": _cache[26] || (_cache[26] = $event => (($data.editingRule.feed_urls) = $event)),
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
                                      ? (_openBlock(), _createElementBlock("ul", _hoisted_20, [
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
                      onClick: _cache[27] || (_cache[27] = $event => ($data.ruleDialog = false))
                    }, {
                      default: _withCtx(() => [...(_cache[69] || (_cache[69] = [
                        _createTextVNode("取消", -1)
                      ]))]),
                      _: 1
                    }),
                    _createVNode(_component_v_btn, {
                      variant: "tonal",
                      "prepend-icon": "mdi-bell-ring-outline",
                      loading: $data.testing,
                      onClick: $options.testCurrentRule
                    }, {
                      default: _withCtx(() => [...(_cache[70] || (_cache[70] = [
                        _createTextVNode(" 通知测试 ", -1)
                      ]))]),
                      _: 1
                    }, 8, ["loading", "onClick"]),
                    _createVNode(_component_v_spacer),
                    _createVNode(_component_v_btn, {
                      color: "primary",
                      loading: $data.savingRule,
                      onClick: $options.saveRule
                    }, {
                      default: _withCtx(() => [...(_cache[71] || (_cache[71] = [
                        _createTextVNode("保存", -1)
                      ]))]),
                      _: 1
                    }, 8, ["loading", "onClick"])
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
                _createElementVNode("span", _hoisted_21, [
                  _createVNode(_component_v_icon, {
                    start: "",
                    color: "primary"
                  }, {
                    default: _withCtx(() => [...(_cache[72] || (_cache[72] = [
                      _createTextVNode("mdi-bell-outline", -1)
                    ]))]),
                    _: 1
                  }),
                  _cache[73] || (_cache[73] = _createTextVNode("通知规则 ", -1))
                ]),
                _cache[74] || (_cache[74] = _createElementVNode("span", { class: "text-caption text-grey ml-2" }, " 监控订阅内容，命中关键词即通过 MP 通知组件提醒你阅读 ", -1))
              ]),
              _: 1
            }),
            _createVNode(_component_v_col, { cols: "auto" }, {
              default: _withCtx(() => [
                _createVNode(_component_v_btn, {
                  color: "primary",
                  "prepend-icon": "mdi-plus",
                  onClick: _cache[29] || (_cache[29] = $event => ($options.openRuleDialog()))
                }, {
                  default: _withCtx(() => [...(_cache[75] || (_cache[75] = [
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
                  ? (_openBlock(), _createElementBlock("span", _hoisted_22, " +" + _toDisplayString(item.keywords.length - 5), 1))
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
                  ? (_openBlock(), _createElementBlock("span", _hoisted_23, _toDisplayString(item.last_hit), 1))
                  : (_openBlock(), _createElementBlock("span", _hoisted_24, "从未命中"))
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
                _createElementVNode("span", _hoisted_25, [
                  _createVNode(_component_v_icon, {
                    start: "",
                    color: "primary"
                  }, {
                    default: _withCtx(() => [...(_cache[76] || (_cache[76] = [
                      _createTextVNode("mdi-history", -1)
                    ]))]),
                    _: 1
                  }),
                  _cache[77] || (_cache[77] = _createTextVNode("最近通知记录 ", -1))
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
                  default: _withCtx(() => [...(_cache[78] || (_cache[78] = [
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
                            default: _withCtx(() => [...(_cache[79] || (_cache[79] = [
                              _createTextVNode("mdi-check-circle-outline", -1)
                            ]))]),
                            _: 1
                          })
                        ]),
                        append: _withCtx(() => [
                          _createElementVNode("span", _hoisted_26, _toDisplayString(log.at), 1)
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
                              _cache[80] || (_cache[80] = _createTextVNode(" 来自 ", -1)),
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
                  default: _withCtx(() => [...(_cache[81] || (_cache[81] = [
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
          default: _withCtx(() => [...(_cache[82] || (_cache[82] = [
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
const AppPage = /*#__PURE__*/_export_sfc(_sfc_main, [['render',_sfc_render],['__scopeId',"data-v-ca1b8d98"]]);

export { AppPage as default };
