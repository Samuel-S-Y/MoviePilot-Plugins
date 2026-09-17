<template>
  <!-- 订阅源列表：桌面端作为左栏卡片，移动端置于抽屉中，两处共用同一组件避免模板重复 -->
  <v-card class="h-100 d-flex flex-column">
    <v-card-title class="text-subtitle-1 d-flex align-center">
      订阅源
      <v-chip size="small" class="ml-2" color="primary" variant="tonal">
        {{ totalUnread }}
      </v-chip>
      <v-spacer />
      <v-btn
        v-if="selectedUrl"
        icon="mdi-check-all"
        size="small"
        variant="text"
        title="标记当前源全部已读"
        aria-label="标记当前源全部已读"
        @click="$emit('mark-all-read', selectedUrl)"
      />
    </v-card-title>
    <v-divider />
    <v-list lines="two" density="comfortable" class="flex-grow-1 overflow-y-auto">
      <v-list-item
        v-for="f in feeds"
        :key="f.url"
        :active="selectedUrl === f.url"
        class="feed-item"
        @click="$emit('select', f.url)"
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
            size="small"
            variant="text"
            color="error"
            title="删除该订阅源"
            aria-label="删除该订阅源"
            @click.stop="$emit('delete', f.url)"
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
</template>

<script>
export default {
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
</script>

<style scoped>
/* 订阅源条目：整块可点，高度 ≥48px 以保证移动端触控命中率 */
.feed-item {
  min-height: 48px;
  cursor: pointer;
}
/* 移动端：本组件内部的图标按钮同样需要达到 44px 触控目标
   （AppPage 的媒体查询作用不到子组件内部元素） */
@media (max-width: 959px) {
  .feed-item :deep(.v-btn) {
    min-width: 44px;
    min-height: 44px;
  }
}
</style>