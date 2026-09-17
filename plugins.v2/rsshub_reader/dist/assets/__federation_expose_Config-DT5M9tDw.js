import { importShared } from './__federation_fn_import-JrT3xvdd.js';
import { _ as _export_sfc } from './_plugin-vue_export-helper-pcqpp-6-.js';

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

const _sfc_main = {
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

const {createTextVNode:_createTextVNode,resolveComponent:_resolveComponent,withCtx:_withCtx,createVNode:_createVNode,createElementVNode:_createElementVNode,openBlock:_openBlock,createElementBlock:_createElementBlock} = await importShared('vue');


const _hoisted_1 = { class: "rsshub-config pa-4" };
const _hoisted_2 = { class: "d-flex align-center mb-3" };
const _hoisted_3 = { class: "d-flex flex-wrap align-center mt-3" };

function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
  const _component_v_icon = _resolveComponent("v-icon");
  const _component_v_spacer = _resolveComponent("v-spacer");
  const _component_v_switch = _resolveComponent("v-switch");
  const _component_v_text_field = _resolveComponent("v-text-field");
  const _component_v_col = _resolveComponent("v-col");
  const _component_v_row = _resolveComponent("v-row");
  const _component_v_select = _resolveComponent("v-select");
  const _component_v_textarea = _resolveComponent("v-textarea");
  const _component_v_btn = _resolveComponent("v-btn");

  return (_openBlock(), _createElementBlock("div", _hoisted_1, [
    _createElementVNode("div", _hoisted_2, [
      _createVNode(_component_v_icon, {
        size: "28",
        color: "primary",
        class: "mr-3"
      }, {
        default: _withCtx(() => [...(_cache[15] || (_cache[15] = [
          _createTextVNode("mdi-rss-box", -1)
        ]))]),
        _: 1
      }),
      _cache[16] || (_cache[16] = _createElementVNode("div", null, [
        _createElementVNode("div", { class: "text-h6" }, "RSSHub 阅读器 · 设置"),
        _createElementVNode("div", { class: "text-caption text-medium-emphasis" }, " 保存配置后生效；关闭开关并保存即停用插件 ")
      ], -1)),
      _createVNode(_component_v_spacer),
      _createVNode(_component_v_switch, {
        modelValue: $data.config.enabled,
        "onUpdate:modelValue": _cache[0] || (_cache[0] = $event => (($data.config.enabled) = $event)),
        color: "success",
        density: "compact",
        "hide-details": "",
        label: $data.config.enabled ? '已启用' : '已停用',
        class: "mt-2"
      }, null, 8, ["modelValue", "label"])
    ]),
    _cache[22] || (_cache[22] = _createElementVNode("div", { class: "text-subtitle-2 mb-1" }, "基础设置", -1)),
    _createVNode(_component_v_row, { dense: "" }, {
      default: _withCtx(() => [
        _createVNode(_component_v_col, {
          cols: "12",
          md: "6"
        }, {
          default: _withCtx(() => [
            _createVNode(_component_v_text_field, {
              modelValue: $data.config.rsshub_base_url,
              "onUpdate:modelValue": _cache[1] || (_cache[1] = $event => (($data.config.rsshub_base_url) = $event)),
              label: "RSSHub 地址",
              density: "compact",
              hint: "局域网 RSSHub 访问地址，如 http://192.168.1.100:1200",
              "persistent-hint": ""
            }, null, 8, ["modelValue"])
          ]),
          _: 1
        }),
        _createVNode(_component_v_col, {
          cols: "6",
          md: "3"
        }, {
          default: _withCtx(() => [
            _createVNode(_component_v_text_field, {
              modelValue: $options.pollInterval,
              "onUpdate:modelValue": _cache[2] || (_cache[2] = $event => (($options.pollInterval) = $event)),
              modelModifiers: { number: true },
              label: "刷新间隔（分钟）",
              type: "number",
              density: "compact",
              hint: "建议 15~60，最小按 5 分钟执行",
              "persistent-hint": ""
            }, null, 8, ["modelValue"])
          ]),
          _: 1
        }),
        _createVNode(_component_v_col, {
          cols: "6",
          md: "3"
        }, {
          default: _withCtx(() => [
            _createVNode(_component_v_text_field, {
              modelValue: $options.maxEntries,
              "onUpdate:modelValue": _cache[3] || (_cache[3] = $event => (($options.maxEntries) = $event)),
              modelModifiers: { number: true },
              label: "每个源保留条数",
              type: "number",
              density: "compact"
            }, null, 8, ["modelValue"])
          ]),
          _: 1
        }),
        _createVNode(_component_v_col, {
          cols: "6",
          md: "3"
        }, {
          default: _withCtx(() => [
            _createVNode(_component_v_text_field, {
              modelValue: $options.maxNotifyLog,
              "onUpdate:modelValue": _cache[4] || (_cache[4] = $event => (($options.maxNotifyLog) = $event)),
              modelModifiers: { number: true },
              label: "通知记录保留条数",
              type: "number",
              density: "compact"
            }, null, 8, ["modelValue"])
          ]),
          _: 1
        }),
        _createVNode(_component_v_col, {
          cols: "6",
          md: "3"
        }, {
          default: _withCtx(() => [
            _createVNode(_component_v_text_field, {
              modelValue: $data.config.opml_group,
              "onUpdate:modelValue": _cache[5] || (_cache[5] = $event => (($data.config.opml_group) = $event)),
              label: "OPML 默认分组",
              density: "compact",
              hint: "OPML 导入未指定分组时使用",
              "persistent-hint": ""
            }, null, 8, ["modelValue"])
          ]),
          _: 1
        })
      ]),
      _: 1
    }),
    _cache[23] || (_cache[23] = _createElementVNode("div", { class: "text-subtitle-2 mt-2 mb-1" }, "阅读与图片", -1)),
    _createVNode(_component_v_row, { dense: "" }, {
      default: _withCtx(() => [
        _createVNode(_component_v_col, {
          cols: "12",
          md: "4"
        }, {
          default: _withCtx(() => [
            _createVNode(_component_v_switch, {
              modelValue: $data.config.fetch_full,
              "onUpdate:modelValue": _cache[6] || (_cache[6] = $event => (($data.config.fetch_full) = $event)),
              label: "抓取正文提取完整图片",
              color: "primary",
              density: "compact",
              "hide-details": ""
            }, null, 8, ["modelValue"])
          ]),
          _: 1
        }),
        _createVNode(_component_v_col, {
          cols: "12",
          md: "4"
        }, {
          default: _withCtx(() => [
            _createVNode(_component_v_switch, {
              modelValue: $data.config.proxy_images,
              "onUpdate:modelValue": _cache[7] || (_cache[7] = $event => (($data.config.proxy_images) = $event)),
              label: "启用后端图片代理",
              color: "primary",
              density: "compact",
              "hide-details": ""
            }, null, 8, ["modelValue"])
          ]),
          _: 1
        }),
        _createVNode(_component_v_col, {
          cols: "12",
          md: "4"
        }, {
          default: _withCtx(() => [
            _createVNode(_component_v_switch, {
              modelValue: $data.config.mark_read_on_open,
              "onUpdate:modelValue": _cache[8] || (_cache[8] = $event => (($data.config.mark_read_on_open) = $event)),
              label: "打开文章自动标为已读",
              color: "primary",
              density: "compact",
              "hide-details": ""
            }, null, 8, ["modelValue"])
          ]),
          _: 1
        })
      ]),
      _: 1
    }),
    _cache[24] || (_cache[24] = _createElementVNode("div", { class: "text-subtitle-2 mt-2 mb-1" }, "规则通知", -1)),
    _createVNode(_component_v_row, { dense: "" }, {
      default: _withCtx(() => [
        _createVNode(_component_v_col, {
          cols: "12",
          md: "4"
        }, {
          default: _withCtx(() => [
            _createVNode(_component_v_switch, {
              modelValue: $data.config.notify_enabled,
              "onUpdate:modelValue": _cache[9] || (_cache[9] = $event => (($data.config.notify_enabled) = $event)),
              label: "启用规则通知",
              color: "primary",
              density: "compact",
              "hide-details": ""
            }, null, 8, ["modelValue"])
          ]),
          _: 1
        }),
        _createVNode(_component_v_col, {
          cols: "12",
          md: "8"
        }, {
          default: _withCtx(() => [
            _createVNode(_component_v_select, {
              modelValue: $data.config.notify_channel,
              "onUpdate:modelValue": _cache[10] || (_cache[10] = $event => (($data.config.notify_channel) = $event)),
              items: $options.channelItems,
              label: "默认通知渠道",
              density: "compact",
              "hide-details": ""
            }, null, 8, ["modelValue", "items"])
          ]),
          _: 1
        }),
        _createVNode(_component_v_col, {
          cols: "12",
          md: "6"
        }, {
          default: _withCtx(() => [
            _createVNode(_component_v_textarea, {
              modelValue: $data.config.notify_template,
              "onUpdate:modelValue": _cache[11] || (_cache[11] = $event => (($data.config.notify_template) = $event)),
              label: "通知内容模板",
              density: "compact",
              rows: "3",
              hint: "支持变量：{title} {feed} {link} {rule} {published}",
              "persistent-hint": ""
            }, null, 8, ["modelValue"])
          ]),
          _: 1
        }),
        _createVNode(_component_v_col, {
          cols: "12",
          md: "6"
        }, {
          default: _withCtx(() => [
            _createVNode(_component_v_text_field, {
              modelValue: $data.config.webhook_url,
              "onUpdate:modelValue": _cache[12] || (_cache[12] = $event => (($data.config.webhook_url) = $event)),
              label: "Webhook 地址",
              density: "compact",
              hint: "渠道选择 Webhook 时，命中规则将 POST JSON 到此地址",
              "persistent-hint": ""
            }, null, 8, ["modelValue"])
          ]),
          _: 1
        })
      ]),
      _: 1
    }),
    _createElementVNode("div", _hoisted_3, [
      _createVNode(_component_v_btn, {
        color: "primary",
        variant: "flat",
        onClick: $options.handleSave
      }, {
        default: _withCtx(() => [
          _createVNode(_component_v_icon, { start: "" }, {
            default: _withCtx(() => [...(_cache[17] || (_cache[17] = [
              _createTextVNode("mdi-content-save", -1)
            ]))]),
            _: 1
          }),
          _cache[18] || (_cache[18] = _createTextVNode("保存 ", -1))
        ]),
        _: 1
      }, 8, ["onClick"]),
      _createVNode(_component_v_btn, {
        class: "ml-2",
        variant: "outlined",
        onClick: _cache[13] || (_cache[13] = $event => (_ctx.$emit('switch')))
      }, {
        default: _withCtx(() => [
          _createVNode(_component_v_icon, { start: "" }, {
            default: _withCtx(() => [...(_cache[19] || (_cache[19] = [
              _createTextVNode("mdi-database-eye-outline", -1)
            ]))]),
            _: 1
          }),
          _cache[20] || (_cache[20] = _createTextVNode("查看数据 ", -1))
        ]),
        _: 1
      }),
      _createVNode(_component_v_spacer),
      _createVNode(_component_v_btn, {
        variant: "text",
        onClick: _cache[14] || (_cache[14] = $event => (_ctx.$emit('close')))
      }, {
        default: _withCtx(() => [...(_cache[21] || (_cache[21] = [
          _createTextVNode("关闭", -1)
        ]))]),
        _: 1
      })
    ])
  ]))
}
const Config = /*#__PURE__*/_export_sfc(_sfc_main, [['render',_sfc_render]]);

export { Config as default };
