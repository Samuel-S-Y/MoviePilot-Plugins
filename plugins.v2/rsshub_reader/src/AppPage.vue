<template>
  <v-container fluid class="app-page">
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
    <!-- 顶部：添加订阅源 + 操作按钮
         移动端重排：输入框整行 + 主操作常显（添加/刷新/仅未读），
         OPML 与图片代理收进「更多」菜单，避免窄屏纵向堆成 7 行 -->
    <v-row class="mb-2" align="center">
      <v-col cols="12" sm="8" md="4">
        <v-text-field
          v-model="newUrl"
          label="RSSHub 路由地址"
          placeholder="如 /douban/movie/hot 的完整 RSS 地址"
          density="compact"
          hide-details
          @keyup.enter="addFeed"
        />
      </v-col>
      <!-- 备注名：移动端隐藏，改用 URL 作为名称，避免独占一整行 -->
      <v-col v-if="!isMobile" cols="12" md="2">
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
      <v-col v-if="!isMobile" cols="auto">
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
      <v-col v-if="!isMobile" cols="auto">
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
      <!-- 移动端「更多」：收纳 OPML 导入导出与图片代理开关 -->
      <v-col v-if="isMobile" cols="auto">
        <v-menu location="bottom end">
          <template #activator="{ props }">
            <v-btn
              icon="mdi-dots-vertical"
              variant="text"
              v-bind="props"
              title="更多操作"
              aria-label="更多操作"
            />
          </template>
          <v-list density="comfortable">
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
            <v-divider class="my-1" />
            <v-list-item>
              <v-switch
                v-model="useProxy"
                label="图片代理"
                density="compact"
                hide-details
                color="primary"
                class="mt-1"
              />
            </v-list-item>
          </v-list>
        </v-menu>
      </v-col>
    </v-row>

    <!-- 全局提示 -->
    <v-row v-if="errorMsg">
      <v-col>
        <v-alert type="error" variant="tonal" density="compact">{{ errorMsg }}</v-alert>
      </v-col>
    </v-row>
    <v-row v-if="infoMsg">
      <v-col>
        <v-alert type="success" variant="tonal" density="compact">{{ infoMsg }}</v-alert>
      </v-col>
    </v-row>

    <!-- 订阅源抽屉：移动端由「☰」按钮或左缘滑出，不占用正文显示空间 -->
    <v-navigation-drawer v-model="drawer" temporary location="left" width="290">
      <RsshubFeedList
        :feeds="feeds"
        :selected-url="selectedUrl"
        :total-unread="totalUnread"
        @select="onDrawerSelect"
        @delete="deleteFeed"
        @mark-all-read="markAllRead"
      />
    </v-navigation-drawer>

    <!-- 主体：桌面端为左（订阅源）+ 中（文章）+ 右（正文）三栏 -->
    <v-row>
      <!-- 左侧：订阅源列表（移动端改用抽屉，此处只在桌面端显示） -->
      <v-col v-if="!isMobile" cols="12" md="3">
        <RsshubFeedList
          :feeds="feeds"
          :selected-url="selectedUrl"
          :total-unread="totalUnread"
          @select="selectFeed"
          @delete="deleteFeed"
          @mark-all-read="markAllRead"
        />
      </v-col>

      <!-- 中栏：当前源的文章列表（简要信息，点选后右栏出正文）；
           移动端与正文单栏互斥切换，避免长距离滚动 -->
      <v-col v-show="!isMobile || mobilePane === 'list'" cols="12" md="4">
        <!-- 未选择订阅源：与左右两栏保持一致的卡片式空状态 -->
        <v-card v-if="!selectedUrl" class="text-center py-10 px-4">
          <v-icon size="64" color="grey-lighten-1" class="mb-3">mdi-rss</v-icon>
          <div class="text-subtitle-1">请选择一个订阅源</div>
          <div class="text-caption text-medium-emphasis mt-1">
            {{ isMobile
              ? '点下方按钮选择订阅源，或用上方输入框添加新的 RSS 地址'
              : '从左侧列表点选，或用上方输入框添加新的 RSS 地址' }}
          </div>
          <!-- 移动端：未选源时「☰」按钮尚不存在（它位于已选源分支内），
               这里提供抽屉入口，避免删除当前源后无处打开订阅源列表 -->
          <v-btn
            v-if="isMobile"
            class="mt-4"
            variant="tonal"
            color="primary"
            prepend-icon="mdi-menu"
            @click="drawer = true"
          >选择订阅源</v-btn>
        </v-card>

        <div v-else>
          <!-- 源标题栏 + 全部已读 -->
          <div class="d-flex align-center mb-2">
            <!-- 移动端：打开订阅源抽屉（桌面端订阅源常驻左栏，无需此按钮） -->
            <v-btn
              v-if="isMobile"
              icon="mdi-menu"
              size="small"
              variant="text"
              class="mr-1"
              title="选择订阅源"
              aria-label="选择订阅源"
              @click="drawer = true"
            />
            <span class="text-subtitle-1 text-truncate mr-2">{{ currentFeedName }}</span>
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

          <!-- 单列列表：entry-list 去掉 grid 的列内边距，卡片间距只由 mb-3 控制 -->
          <v-row class="entry-list">
            <v-col
              v-for="(art, idx) in visibleEntries"
              :key="artKey(art, idx)"
              cols="12"
            >
              <v-card
                class="entry-card mb-3"
                :class="{
                  'is-read': art.is_read,
                  'is-active': art.link && art.link === current.link,
                }"
                hover
                @click="openArticle(art)"
              >
                <div class="d-flex align-start">
                  <!-- 小缩略图：有图时显示，走后端图片代理绕过防盗链 -->
                  <v-img
                    v-if="art.thumbnail"
                    :src="imgUrl(art.thumbnail)"
                    :width="isMobile ? 64 : 56"
                    :height="isMobile ? 64 : 56"
                    cover
                    class="entry-thumb"
                    loading="lazy"
                    decoding="async"
                  >
                    <template #placeholder>
                      <div class="d-flex align-center justify-center fill-height">
                        <v-progress-circular indeterminate size="16" />
                      </div>
                    </template>
                  </v-img>
                  <div class="flex-grow-1 min-w-0">
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
                  </div>
                </div>
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

          <!-- 该源没有可展示的文章：卡片式空状态，并给出可直接点击的操作入口 -->
          <v-card v-if="!visibleEntries.length" class="text-center py-10 px-4">
            <v-icon size="64" color="grey-lighten-1" class="mb-3">
              {{ showUnreadOnly ? 'mdi-email-check-outline' : 'mdi-rss-off' }}
            </v-icon>
            <div class="text-subtitle-1">
              {{ showUnreadOnly ? '没有未读文章' : '该源暂无文章' }}
            </div>
            <div class="text-caption text-medium-emphasis mt-1">
              {{ showUnreadOnly
                ? '当前已过滤已读文章，关闭「仅未读」即可查看全部'
                : '可能是刚添加的源或该源本身内容为空，点「刷新」重新拉取' }}
            </div>
            <div class="d-flex justify-center flex-wrap mt-4">
              <v-btn
                v-if="showUnreadOnly"
                class="ma-1"
                variant="tonal"
                prepend-icon="mdi-filter-off-outline"
                @click="showUnreadOnly = false"
              >查看全部</v-btn>
              <v-btn
                class="ma-1"
                variant="tonal"
                color="primary"
                prepend-icon="mdi-refresh"
                :loading="refreshing"
                @click="refreshAll"
              >刷新</v-btn>
            </div>
          </v-card>
        </div>
      </v-col>

      <!-- 右栏：选中文章的完整内容（移动端与文章列表单栏切换） -->
      <v-col v-show="!isMobile || mobilePane === 'content'" cols="12" md="5">
        <v-card ref="contentPane">
          <!-- 移动端：返回文章列表，替代长距离滚动 -->
          <div v-if="isMobile" class="pt-2 pl-2">
            <v-btn
              variant="text"
              prepend-icon="mdi-arrow-left"
              @click="mobilePane = 'list'"
            >返回列表</v-btn>
          </div>
          <template v-if="current.title">
            <v-card-title class="text-subtitle-1">
              {{ current.title }}
            </v-card-title>
            <v-card-subtitle class="pb-1">
              <span v-if="current.author">{{ current.author }} · </span>
              <span v-if="current.published">{{ current.published }}</span>
            </v-card-subtitle>
            <v-card-actions class="pt-1">
              <v-btn
                size="small"
                variant="text"
                :prepend-icon="current.is_read ? 'mdi-email' : 'mdi-email-open'"
                @click="toggleRead(current)"
              >
                {{ current.is_read ? '标为未读' : '标为已读' }}
              </v-btn>
              <v-btn
                v-if="current.link"
                size="small"
                variant="text"
                prepend-icon="mdi-open-in-new"
                :href="current.link"
                target="_blank"
              >原文</v-btn>
              <v-spacer />
              <v-btn
                size="small"
                variant="text"
                prepend-icon="mdi-close"
                @click="closeArticle"
              >关闭</v-btn>
            </v-card-actions>
            <v-divider />

            <v-card-text>
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
                    cols="6" sm="4"
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
              <v-alert v-else-if="!contentLoading" type="info" variant="tonal" density="compact">
                该文章未提取到图片
              </v-alert>

              <!-- 正文（富文本，图片走代理）：RSS 只给摘要时先展示抓取进度 -->
              <div
                v-if="contentLoading"
                class="d-flex align-center text-medium-emphasis my-4"
              >
                <v-progress-circular indeterminate size="20" class="mr-2" />
                正在抓取原文正文…
              </div>
              <div
                v-else-if="current.content"
                class="article-content"
                v-html="proxiedContent"
              />
              <v-alert v-else type="warning" variant="tonal">
                无正文内容（可在插件设置中开启『抓取正文提取完整图片』后刷新）
              </v-alert>
            </v-card-text>
          </template>

          <!-- 未选择文章时的空状态 -->
          <v-card-text v-else class="text-center text-grey py-12">
            <v-icon size="56" class="mb-3">mdi-book-open-page-variant-outline</v-icon>
            <div>请在中间选择一篇文章</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

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
            :disabled="!opmlFileObj"
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
          <v-btn
            variant="tonal"
            prepend-icon="mdi-bell-ring-outline"
            :loading="testing"
            @click="testCurrentRule"
          >
            通知测试
          </v-btn>
          <v-spacer />
          <v-btn color="primary" :loading="savingRule" @click="saveRule">保存</v-btn>
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

// 订阅源列表组件：桌面左栏与移动端抽屉共用，避免模板重复
import RsshubFeedList from "./FeedList.vue";

export default {
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
/* 单列列表：去掉 grid 的行列内边距，卡片间距只由 mb-3 控制，避免上下间距不均 */
.entry-list {
  margin: 0;
}
.entry-list > .v-col {
  padding: 0;
}
/* 中栏文章卡片：明确的白底 + 细边框，与页面背景区分开；hover 时边框转主题色并轻微抬升 */
.entry-card {
  background: rgb(var(--v-theme-surface));
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.entry-card:hover {
  border-color: rgb(var(--v-theme-primary));
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}
/* 已读：只弱化文字、保留卡片形态，避免整块变灰显得脏 */
.entry-card.is-read {
  background: rgba(var(--v-theme-on-surface), 0.02);
}
.entry-card.is-read .v-card-title,
.entry-card.is-read .v-card-text {
  opacity: 0.7;
}
/* 中栏当前选中的文章：左侧高亮条 + 淡色底，与右栏内容对应 */
.entry-card.is-active {
  border-left: 3px solid rgb(var(--v-theme-primary));
  background: rgba(var(--v-theme-primary), 0.06);
}
/* 收紧卡片内部留白：中栏卡片是列表项，不需要 Vuetify 默认的大间距 */
.entry-card .v-card-title {
  padding: 12px 12px 2px;
  font-size: 0.875rem;
  line-height: 1.4;
}
.entry-card .v-card-subtitle {
  padding: 0 12px;
  font-size: 0.7rem;
  opacity: 0.7;
}
.entry-card .v-card-text {
  padding: 6px 12px 0;
  font-size: 0.8rem;
  line-height: 1.5;
}
.entry-card .v-card-actions {
  padding: 2px 8px 6px;
  min-block-size: auto;
}

/* ============ 移动端适配（<960px，对应 Vuetify smAndDown）============ */
@media (max-width: 959px) {
  /* 可点元素最小 44×44px：符合触控目标尺寸建议，降低误触
     （加 .app-page 前缀是为了让构建的自定义过滤插件保留该规则） */
  .app-page .v-btn {
    min-height: 44px;
  }
  .app-page .v-btn--icon {
    min-width: 44px;
  }
  /* 正文 16px / 行距 1.75：移动阅读更舒适，同时避免 iOS 聚焦时自动放大 */
  /* 用 .app-page 提升特异性，确保覆盖文末的桌面基线字号 */
  .app-page .article-content {
    font-size: 16px;
    line-height: 1.75;
  }
  /* v-html 渲染的正文内容不携带 scope 属性，需用 :deep 才能命中内部 img */
  .article-content :deep(img) {
    max-width: 100%;
    height: auto;
  }
  /* 中栏卡片在窄屏放大字号，提升可读性 */
  .entry-card .v-card-title {
    font-size: 1rem;
  }
  .entry-card .v-card-text {
    font-size: 0.875rem;
  }
}
/* 中栏卡片左侧小缩略图：固定方形不参与伸缩，圆角与卡片留白协调 */
.entry-thumb {
  flex: 0 0 auto;
  margin: 12px 0 0 12px;
  border-radius: 6px;
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
