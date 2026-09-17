import { importShared } from './__federation_fn_import-JrT3xvdd.js';
import { _ as _export_sfc } from './_plugin-vue_export-helper-pcqpp-6-.js';

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

const _sfc_main = {
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

const {createTextVNode:_createTextVNode,resolveComponent:_resolveComponent,withCtx:_withCtx,createVNode:_createVNode,createElementVNode:_createElementVNode,toDisplayString:_toDisplayString,openBlock:_openBlock,createBlock:_createBlock,createCommentVNode:_createCommentVNode,renderList:_renderList,Fragment:_Fragment,createElementBlock:_createElementBlock} = await importShared('vue');


const _hoisted_1 = { class: "rsshub-page pa-4" };
const _hoisted_2 = { class: "d-flex align-center mb-3" };
const _hoisted_3 = { class: "text-h5" };
const _hoisted_4 = { class: "text-h5" };
const _hoisted_5 = { class: "d-flex flex-wrap align-center mt-3" };

function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
  const _component_v_icon = _resolveComponent("v-icon");
  const _component_v_card_text = _resolveComponent("v-card-text");
  const _component_v_card = _resolveComponent("v-card");
  const _component_v_col = _resolveComponent("v-col");
  const _component_v_row = _resolveComponent("v-row");
  const _component_v_alert = _resolveComponent("v-alert");
  const _component_v_list_item_title = _resolveComponent("v-list-item-title");
  const _component_v_list_item = _resolveComponent("v-list-item");
  const _component_v_list = _resolveComponent("v-list");
  const _component_v_btn = _resolveComponent("v-btn");
  const _component_v_spacer = _resolveComponent("v-spacer");

  return (_openBlock(), _createElementBlock("div", _hoisted_1, [
    _createElementVNode("div", _hoisted_2, [
      _createVNode(_component_v_icon, {
        size: "30",
        color: "primary",
        class: "mr-3"
      }, {
        default: _withCtx(() => [...(_cache[1] || (_cache[1] = [
          _createTextVNode("mdi-rss-box", -1)
        ]))]),
        _: 1
      }),
      _cache[2] || (_cache[2] = _createElementVNode("div", null, [
        _createElementVNode("div", { class: "text-h6" }, "RSSHub 阅读器"),
        _createElementVNode("div", { class: "text-caption text-medium-emphasis" }, " 订阅源管理 · 文章阅读 · 规则通知 ")
      ], -1))
    ]),
    _createVNode(_component_v_row, { dense: "" }, {
      default: _withCtx(() => [
        _createVNode(_component_v_col, { cols: "6" }, {
          default: _withCtx(() => [
            _createVNode(_component_v_card, {
              variant: "tonal",
              color: "primary",
              loading: $data.loading
            }, {
              default: _withCtx(() => [
                _createVNode(_component_v_card_text, { class: "py-3 text-center" }, {
                  default: _withCtx(() => [
                    _createElementVNode("div", _hoisted_3, _toDisplayString($data.feedCount), 1),
                    _cache[3] || (_cache[3] = _createElementVNode("div", { class: "text-caption" }, "订阅源", -1))
                  ]),
                  _: 1
                })
              ]),
              _: 1
            }, 8, ["loading"])
          ]),
          _: 1
        }),
        _createVNode(_component_v_col, { cols: "6" }, {
          default: _withCtx(() => [
            _createVNode(_component_v_card, {
              variant: "tonal",
              color: "warning",
              loading: $data.loading
            }, {
              default: _withCtx(() => [
                _createVNode(_component_v_card_text, { class: "py-3 text-center" }, {
                  default: _withCtx(() => [
                    _createElementVNode("div", _hoisted_4, _toDisplayString($data.unreadCount), 1),
                    _cache[4] || (_cache[4] = _createElementVNode("div", { class: "text-caption" }, "未读文章", -1))
                  ]),
                  _: 1
                })
              ]),
              _: 1
            }, 8, ["loading"])
          ]),
          _: 1
        })
      ]),
      _: 1
    }),
    ($data.errorMsg)
      ? (_openBlock(), _createBlock(_component_v_alert, {
          key: 0,
          type: "error",
          variant: "tonal",
          density: "compact",
          class: "mt-3"
        }, {
          default: _withCtx(() => [
            _createTextVNode(_toDisplayString($data.errorMsg), 1)
          ]),
          _: 1
        }))
      : _createCommentVNode("", true),
    _createVNode(_component_v_list, {
      density: "compact",
      class: "my-2"
    }, {
      default: _withCtx(() => [
        (_openBlock(true), _createElementBlock(_Fragment, null, _renderList($data.features, (item) => {
          return (_openBlock(), _createBlock(_component_v_list_item, {
            key: item.text
          }, {
            prepend: _withCtx(() => [
              _createVNode(_component_v_icon, { color: "primary" }, {
                default: _withCtx(() => [
                  _createTextVNode(_toDisplayString(item.icon), 1)
                ]),
                _: 2
              }, 1024)
            ]),
            default: _withCtx(() => [
              _createVNode(_component_v_list_item_title, { class: "text-body-2" }, {
                default: _withCtx(() => [
                  _createTextVNode(_toDisplayString(item.text), 1)
                ]),
                _: 2
              }, 1024)
            ]),
            _: 2
          }, 1024))
        }), 128))
      ]),
      _: 1
    }),
    _createElementVNode("div", _hoisted_5, [
      _createVNode(_component_v_btn, {
        color: "primary",
        variant: "flat",
        onClick: $options.openAppPage
      }, {
        default: _withCtx(() => [
          _createVNode(_component_v_icon, { start: "" }, {
            default: _withCtx(() => [...(_cache[5] || (_cache[5] = [
              _createTextVNode("mdi-open-in-new", -1)
            ]))]),
            _: 1
          }),
          _cache[6] || (_cache[6] = _createTextVNode("打开 RSS 阅读器 ", -1))
        ]),
        _: 1
      }, 8, ["onClick"]),
      ($props.show_switch)
        ? (_openBlock(), _createBlock(_component_v_btn, {
            key: 0,
            class: "ml-2",
            variant: "outlined",
            onClick: $options.openConfig
          }, {
            default: _withCtx(() => [
              _createVNode(_component_v_icon, { start: "" }, {
                default: _withCtx(() => [...(_cache[7] || (_cache[7] = [
                  _createTextVNode("mdi-cog-outline", -1)
                ]))]),
                _: 1
              }),
              _cache[8] || (_cache[8] = _createTextVNode("设置 ", -1))
            ]),
            _: 1
          }, 8, ["onClick"]))
        : _createCommentVNode("", true),
      _createVNode(_component_v_btn, {
        class: "ml-2",
        variant: "outlined",
        loading: $data.refreshing,
        onClick: $options.refreshAll
      }, {
        default: _withCtx(() => [
          _createVNode(_component_v_icon, { start: "" }, {
            default: _withCtx(() => [...(_cache[9] || (_cache[9] = [
              _createTextVNode("mdi-refresh", -1)
            ]))]),
            _: 1
          }),
          _cache[10] || (_cache[10] = _createTextVNode("立即刷新 ", -1))
        ]),
        _: 1
      }, 8, ["loading", "onClick"]),
      _createVNode(_component_v_spacer),
      _createVNode(_component_v_btn, {
        variant: "text",
        onClick: _cache[0] || (_cache[0] = $event => (_ctx.$emit('close')))
      }, {
        default: _withCtx(() => [...(_cache[11] || (_cache[11] = [
          _createTextVNode("关闭", -1)
        ]))]),
        _: 1
      })
    ])
  ]))
}
const Page = /*#__PURE__*/_export_sfc(_sfc_main, [['render',_sfc_render]]);

export { Page as default };
