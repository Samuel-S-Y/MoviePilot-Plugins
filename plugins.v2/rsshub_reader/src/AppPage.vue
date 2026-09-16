<template>
  <v-container fluid>
    <!-- 顶部 Tab 导航：订阅源 / 通知规则 -->
    <v-tabs v-model="currentTab" color="primary" density="comfortable" class="mb-3">
      <v-tab value="feeds">
        <v-icon start size="small">mdi-rss</v-icon>订阅源
      </v-tab>
      <v-tab value="rules">
        <v-icon start size="small">mdi-bell-outline</v-icon>通知规则
        <v-chip v-if="rules.length" size="x-small" class="ml-2" color="primary" variant="tonal">
          {{ rules.length }}
        </v-chip>
      </v-tab>
    </v-tabs>

    <!-- ================= 视图一：订阅源 + 文章 ================= -->
    <div v-show="currentTab === 'feeds'">
    <!-- 顶部：添加订阅源 + 操作按钮 -->
    <v-row class="mb-2" align="center">
      <v-col cols="12" md="4">
        <v-text-field
          v-model="newUrl"
          label="RSSHub 路由地址"
          placeholder="如 /douban/movie/hot 的完整 RSS 地址"
          density="compact"
          hide-details
          @keyup.enter="addFeed"
        />
      </v-col>
      <v-col cols="12" md="2">
        <v-text-field
          v-model="newName"
          label="备注名（可选）"
          density="compact"
          hide-details
        />
      </v-col>
      <v-col cols="auto">
        <v-btn color="primary" :loading="adding" @click="addFeed">添加</v-btn>
      </v-col>
      <v-col cols="auto">
        <v-btn variant="outlined" :loading="refreshing" @click="refreshAll">
          <v-icon start>mdi-refresh</v-icon>刷新
        </v-btn>
      </v-col>
      <v-col cols="auto">
        <v-menu>
          <template #activator="{ props }">
            <v-btn variant="tonal" v-bind="props">
              <v-icon start>mdi-import-export</v-icon>OPML
            </v-btn>
          </template>
          <v-list density="compact">
            <v-list-item @click="downloadOpml">
              <v-list-item-title>
                <v-icon start size="small">mdi-export</v-icon>导出订阅源
              </v-list-item-title>
            </v-list-item>
            <v-list-item @click="importDialog = true">
              <v-list-item-title>
                <v-icon start size="small">mdi-import</v-icon>导入 OPML
              </v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>
      </v-col>
      <v-col cols="auto">
        <v-switch
          v-model="useProxy"
          label="图片代理"
          density="compact"
          hide-details
          color="primary"
        />
      </v-col>
      <v-col cols="auto">
        <v-switch
          v-model="showUnreadOnly"
          label="仅未读"
          density="compact"
          hide-details
          color="primary"
        />
      </v-col>
    </v-row>

    <!-- 全局提示 -->
    <v-row v-if="errorMsg">
      <v-col>
        <v-alert type="error" variant="tonal" dense>{{ errorMsg }}</v-alert>
      </v-col>
    </v-row>
    <v-row v-if="infoMsg">
      <v-col>
        <v-alert type="success" variant="tonal" dense>{{ infoMsg }}</v-alert>
      </v-col>
    </v-row>

    <!-- 主体：左侧订阅源 + 右侧文章 -->
    <v-row>
      <!-- 左侧：订阅源列表（含未读数角标） -->
      <v-col cols="12" md="3">
        <v-card>
          <v-card-title class="text-subtitle-1 d-flex align-center">
            订阅源
            <v-chip size="small" class="ml-2" color="primary" variant="tonal">
              {{ totalUnread }}
            </v-chip>
            <v-spacer />
            <v-btn
              v-if="selectedUrl"
              icon="mdi-check-all"
              size="x-small"
              variant="text"
              title="标记当前源全部已读"
              @click="markAllRead(selectedUrl)"
            />
          </v-card-title>
          <v-divider />
          <v-list lines="two" density="compact">
            <v-list-item
              v-for="f in feeds"
              :key="f.url"
              :active="selectedUrl === f.url"
              @click="selectFeed(f.url)"
            >
              <v-list-item-title>
                {{ f.name }}
                <v-chip
                  v-if="f.unread > 0"
                  size="x-small"
                  color="error"
                  variant="flat"
                  class="ml-1"
                >{{ f.unread }}</v-chip>
              </v-list-item-title>
              <v-list-item-subtitle>
                <span v-if="f.group" class="text-primary">{{ f.group }} · </span>
                {{ f.title || '加载中...' }} · {{ f.count || 0 }} 篇
              </v-list-item-subtitle>
              <template #append>
                <v-btn
                  icon="mdi-delete"
                  size="x-small"
                  variant="text"
                  color="error"
                  @click.stop="deleteFeed(f.url)"
                />
              </template>
            </v-list-item>
            <v-list-item v-if="!feeds.length">
              <v-list-item-title class="text-grey">
                暂无订阅源，点 OPML → 导入 或从 RSSHub 添加
              </v-list-item-title>
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>

      <!-- 右侧：文章列表 -->
      <v-col cols="12" md="9">
        <v-card v-if="!selectedUrl">
          <v-card-text class="text-grey">请从左侧选择一个订阅源</v-card-text>
        </v-card>

        <div v-else>
          <!-- 源标题栏 + 全部已读 -->
          <div class="d-flex align-center mb-2">
            <span class="text-subtitle-1">{{ currentFeedName }}</span>
            <v-spacer />
            <v-btn
              size="small"
              variant="text"
              prepend-icon="mdi-check-all"
              @click="markAllRead(selectedUrl)"
            >
              全部标为已读
            </v-btn>
          </div>

          <v-row>
            <v-col
              v-for="(art, idx) in visibleEntries"
              :key="artKey(art, idx)"
              cols="12"
              sm="6"
              md="4"
            >
              <v-card
                class="h-100 entry-card"
                :class="{ 'is-read': art.is_read }"
                hover
                @click="openArticle(art)"
              >
                <!-- 首图（走代理） -->
                <v-img
                  v-if="art.thumbnail"
                  :src="imgUrl(art.thumbnail)"
                  height="140"
                  cover
                  gradient="to bottom, rgba(0,0,0,0) 60%, rgba(0,0,0,0.5)"
                >
                  <template #placeholder>
                    <div class="d-flex align-center justify-center fill-height">
                      <v-progress-circular indeterminate size="24" />
                    </div>
                  </template>
                </v-img>
                <v-card-title class="text-subtitle-2 two-line">
                  <v-icon
                    v-if="!art.is_read"
                    size="x-small"
                    color="primary"
                    class="mr-1"
                  >mdi-circle-medium</v-icon>
                  {{ art.title }}
                </v-card-title>
                <v-card-subtitle v-if="art.published">
                  {{ art.published }}
                </v-card-subtitle>
                <v-card-text class="text-body-2 text-grey-darken-1 clamp-2">
                  {{ art.summary }}
                </v-card-text>
                <v-card-actions>
                  <v-chip
                    v-if="art.images && art.images.length"
                    size="small"
                    color="primary"
                    variant="tonal"
                  >
                    <v-icon start size="x-small">mdi-image</v-icon>
                    {{ art.images.length }}
                  </v-chip>
                  <v-spacer />
                  <!-- 已读/未读切换 -->
                  <v-btn
                    :icon="art.is_read ? 'mdi-email-open' : 'mdi-email'"
                    size="x-small"
                    variant="text"
                    :title="art.is_read ? '标为未读' : '标为已读'"
                    @click.stop="toggleRead(art)"
                  />
                  <v-btn
                    icon="mdi-open-in-new"
                    size="x-small"
                    variant="text"
                    :href="art.link"
                    target="_blank"
                    @click.stop
                  />
                </v-card-actions>
              </v-card>
            </v-col>
          </v-row>

          <v-empty-state
            v-if="!visibleEntries.length"
            icon="mdi-rss-off"
            :title="showUnreadOnly ? '没有未读文章 🎉' : '该源暂无文章'"
            text="尝试点一下『刷新』"
          />
        </div>
      </v-col>
    </v-row>

    <!-- 文章详情对话框：正文 + 图片画廊 -->
    <v-dialog v-model="dialog" fullscreen transition="dialog-bottom-transition">
      <v-card>
        <v-toolbar color="primary" density="compact">
          <v-btn icon="mdi-close" @click="dialog = false" />
          <v-toolbar-title>{{ current.title }}</v-toolbar-title>
          <v-spacer />
          <v-btn
            :prepend-icon="current.is_read ? 'mdi-email' : 'mdi-email-open'"
            variant="text"
            @click="toggleRead(current)"
          >
            {{ current.is_read ? '标为未读' : '标为已读' }}
          </v-btn>
          <v-btn
            v-if="current.link"
            :href="current.link"
            target="_blank"
            variant="text"
          >原文</v-btn>
        </v-toolbar>

        <v-container fluid>
          <div class="text-caption text-grey mb-2">
            <span v-if="current.author">{{ current.author }} · </span>
            <span v-if="current.published">{{ current.published }}</span>
          </div>

          <!-- 图片画廊 -->
          <div v-if="current.images && current.images.length" class="mb-4">
            <div class="text-subtitle-2 mb-2">
              <v-icon start size="small">mdi-image-multiple</v-icon>
              图片 ({{ current.images.length }})
            </div>
            <v-row>
              <v-col
                v-for="(img, i) in current.images"
                :key="i"
                cols="6"
                sm="4"
                md="3"
              >
                <v-img
                  :src="imgUrl(img)"
                  aspect-ratio="1"
                  cover
                  class="rounded"
                  @click="preview(i)"
                >
                  <template #placeholder>
                    <div class="d-flex align-center justify-center fill-height">
                      <v-progress-circular indeterminate size="20" />
                    </div>
                  </template>
                </v-img>
              </v-col>
            </v-row>
          </div>
          <v-alert v-else type="info" variant="tonal" density="compact">
            该文章未提取到图片
          </v-alert>

          <!-- 正文（富文本，图片走代理） -->
          <div
            v-if="current.content"
            class="article-content"
            v-html="proxiedContent"
          />
          <v-alert v-else type="warning" variant="tonal">
            无正文内容（可开启『抓取正文』重新刷新）
          </v-alert>
        </v-container>
      </v-card>
    </v-dialog>

    <!-- 图片大图预览 -->
    <v-dialog v-model="previewDialog" max-width="900">
      <v-img :src="previewUrl" max-height="80vh" contain>
        <template #placeholder>
          <div class="d-flex align-center justify-center fill-height">
            <v-progress-circular indeterminate />
          </div>
        </template>
      </v-img>
    </v-dialog>

    <!-- OPML 导入对话框 -->
    <v-dialog v-model="importDialog" max-width="600">
      <v-card>
        <v-card-title>导入 OPML</v-card-title>
        <v-card-text>
          <p class="text-caption text-grey">
            支持 Feedly / Inoreader / Miniflux / FreshRSS 等导出的 OPML 1.0/2.0。
            已存在的源会自动跳过，不重复添加。
          </p>
          <v-file-input
            v-model="opmlFile"
            label="选择 .opml 文件"
            accept=".opml,.xml,text/xml"
            density="compact"
            prepend-icon="mdi-file-upload"
          />
          <v-text-field
            v-model="opmlGroup"
            label="分组（可选）"
            placeholder="留空则使用 OPML 内的文件夹结构"
            density="compact"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="importDialog = false">取消</v-btn>
          <v-btn
            color="primary"
            :loading="importing"
            :disabled="!opmlFile"
            @click="importOpml"
          >导入</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 规则编辑对话框 -->
    <v-dialog v-model="ruleDialog" max-width="720" persistent>
      <v-card>
        <v-card-title>{{ editingRule.id ? '编辑规则' : '新建规则' }}</v-card-title>
        <v-card-text>
          <v-row dense>
            <v-col cols="12">
              <v-text-field
                v-model="editingRule.name"
                label="规则名称"
                placeholder="例如：重要科技新闻"
                density="compact"
                :rules="[v => !!v.trim() || '规则名称不能为空']"
              />
            </v-col>
            <v-col cols="12" md="6">
              <v-select
                v-model="editingRule.match_type"
                :items="matchTypeItems"
                label="匹配方式"
                density="compact"
              />
            </v-col>
            <v-col cols="12" md="6">
              <v-select
                v-model="editingRule.channel"
                :items="channelItems"
                label="通知渠道（留空用全局默认）"
                density="compact"
                clearable
              />
            </v-col>
            <v-col cols="12">
              <v-combobox
                v-model="editingRule.keywords"
                label="正向关键词（每行/每项一个，OR 逻辑）"
                placeholder="输入后回车添加，如 AI、GPT"
                density="compact"
                multiple
                chips
                closable-chips
              />
            </v-col>
            <v-col cols="12">
              <v-label class="text-caption">匹配字段（可多选）</v-label>
              <v-checkbox
                v-for="opt in fieldOptions"
                :key="opt.value"
                v-model="editingRule.fields"
                :label="opt.title"
                :value="opt.value"
                density="compact"
                hide-details
                class="mr-4 d-inline-flex"
              />
            </v-col>
            <v-col cols="12">
              <v-select
                v-model="editingRule.feed_urls"
                :items="feedUrlItems"
                label="适用订阅源（留空 = 全部源）"
                density="compact"
                multiple
                chips
                clearable
              />
            </v-col>
            <v-col cols="12">
              <v-alert
                v-if="testResult"
                :type="testResult.ok ? 'success' : 'warning'"
                variant="tonal"
                density="compact"
              >
                {{ testResult.msg }}
                <ul v-if="testResult.hits && testResult.hits.length" class="mt-1 mb-0">
                  <li v-for="(h, i) in testResult.hits.slice(0, 10)" :key="i">
                    [{{ h.feed }}] {{ h.title }}
                  </li>
                </ul>
              </v-alert>
            </v-col>
          </v-row>
        </v-card-text>
        <v-card-actions>
          <v-btn variant="text" @click="ruleDialog = false">取消</v-btn>
          <v-btn variant="tonal" prepend-icon="mdi-play-circle-outline" @click="testCurrentRule">
            试运行
          </v-btn>
          <v-spacer />
          <v-btn color="primary" @click="saveRule">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    </div>
    <!-- ================= end 视图一：订阅源 + 文章 ================= -->

    <!-- ================= 视图二：通知规则 ================= -->
    <div v-show="currentTab === 'rules'">
      <v-row class="mb-2" align="center">
        <v-col cols="12" md="6">
          <span class="text-subtitle-1 font-weight-medium">
            <v-icon start color="primary">mdi-bell-outline</v-icon>通知规则
          </span>
          <span class="text-caption text-grey ml-2">
            监控订阅内容，命中关键词即通过 MP 通知组件提醒你阅读
          </span>
        </v-col>
        <v-col cols="auto">
          <v-btn color="primary" prepend-icon="mdi-plus" @click="openRuleDialog()">
            新建规则
          </v-btn>
        </v-col>
      </v-row>

      <!-- 规则列表 -->
      <v-card>
        <v-data-table
          :headers="ruleHeaders"
          :items="rules"
          :loading="rulesLoading"
          density="comfortable"
          no-data-text="还没有规则，点右上角「新建规则」开始配置"
          item-value="id"
          hide-default-footer
          :items-per-page="-1"
        >
          <template #item.enabled="{ item }">
            <v-switch
              :model-value="item.enabled"
              density="compact"
              hide-details
              color="primary"
              @update:model-value="toggleRule(item, $event)"
            />
          </template>
          <template #item.fields="{ item }">
            <v-chip
              v-for="f in item.fields"
              :key="f"
              size="x-small"
              class="mr-1"
              variant="tonal"
            >{{ fieldLabel(f) }}</v-chip>
          </template>
          <template #item.keywords="{ item }">
            <v-chip
              v-for="(k, i) in item.keywords.slice(0, 5)"
              :key="i"
              size="x-small"
              color="primary"
              variant="tonal"
              class="mr-1"
            >{{ k }}</v-chip>
            <span v-if="item.keywords.length > 5" class="text-caption text-grey">
              +{{ item.keywords.length - 5 }}
            </span>
          </template>
          <template #item.match_type="{ item }">
            {{ matchTypeLabel(item.match_type) }}
          </template>
          <template #item.channel="{ item }">
            {{ item.channel || '默认' }}
          </template>
          <template #item.last_hit="{ item }">
            <span v-if="item.last_hit" class="text-caption">{{ item.last_hit }}</span>
            <span v-else class="text-caption text-grey">从未命中</span>
          </template>
          <template #item.actions="{ item }">
            <v-btn
              icon="mdi-play-circle-outline"
              size="x-small"
              variant="text"
              title="试运行（不发送通知）"
              @click="testRule(item)"
            />
            <v-btn
              icon="mdi-pencil-outline"
              size="x-small"
              variant="text"
              title="编辑"
              @click="openRuleDialog(item)"
            />
            <v-btn
              icon="mdi-delete-outline"
              size="x-small"
              variant="text"
              color="error"
              title="删除"
              @click="deleteRule(item)"
            />
          </template>
        </v-data-table>
      </v-card>

      <!-- 最近通知记录 -->
      <v-row class="mt-4" align="center">
        <v-col cols="12" md="6">
          <span class="text-subtitle-1 font-weight-medium">
            <v-icon start color="primary">mdi-history</v-icon>最近通知记录
          </span>
        </v-col>
        <v-col cols="auto">
          <v-btn
            variant="text"
            size="small"
            prepend-icon="mdi-delete-sweep-outline"
            :disabled="!notifyLog.length"
            @click="clearLog"
          >清空记录</v-btn>
        </v-col>
      </v-row>
      <v-card>
        <v-list v-if="notifyLog.length" lines="two" density="compact">
          <v-list-item v-for="(log, i) in notifyLog" :key="i">
            <template #prepend>
              <v-icon color="success">mdi-check-circle-outline</v-icon>
            </template>
            <v-list-item-title>
              {{ log.title }}
            </v-list-item-title>
            <v-list-item-subtitle>
              来自 <b>{{ log.feed }}</b> · 命中规则「{{ log.rule }}」· 渠道 {{ log.channel }}
            </v-list-item-subtitle>
            <template #append>
              <span class="text-caption text-grey">{{ log.at }}</span>
            </template>
          </v-list-item>
        </v-list>
        <v-alert v-else type="info" variant="tonal" density="compact">
          暂无通知记录。命中规则的文章会在这里出现，并同步到 MP 通知组件。
        </v-alert>
      </v-card>

      <!-- 行为说明 -->
      <v-alert
        type="info"
        variant="tonal"
        density="compact"
        class="mt-4"
        icon="mdi-information-outline"
      >
        <b>规则行为：</b>
        每次刷新订阅源时，仅对<b>首次出现</b>的新条目匹配；已读条目不通知；
        命中后<b>逐条即时</b>发送并自动标为已读，去重不重复打扰。
      </v-alert>
    </div>
    <!-- ================= end 视图二：通知规则 ================= -->

  </v-container>
</template>

<script>
// 兼容 MP 前端对插件 API 响应的两种形态：
// 1) 包装形态 {success: true, data: {...}} → 取 data；
// 2) 端点直接返回的 JSON {ok: true, ...} → 原样返回。
function unwrapResponse(res) {
  if (res && typeof res === "object" && "success" in res && "data" in res) {
    return res.data;
  }
  return res;
}

export default {
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
</script>

<style scoped>
.two-line {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
/* 已读文章置灰、弱化 */
.entry-card.is-read .v-card-title,
.entry-card.is-read .v-card-text {
  opacity: 0.55;
}
.entry-card.is-read {
  background: rgba(0, 0, 0, 0.02);
}
.article-content {
  max-width: 820px;
  margin: 0 auto;
  line-height: 1.8;
  font-size: 15px;
}
.article-content :deep(img) {
  max-width: 100%;
  height: auto;
  display: block;
  margin: 12px auto;
  border-radius: 4px;
}
.article-content :deep(a) {
  color: var(--v-theme-primary);
}
.article-content :deep(blockquote) {
  border-left: 4px solid #ccc;
  padding-left: 12px;
  color: #666;
}
</style>
