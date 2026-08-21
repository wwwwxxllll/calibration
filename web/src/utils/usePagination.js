import { ref, computed, watch } from 'vue';

/**
 * 通用分页：传入列表 ref/computed，返回当前页、总页数、当页数据与翻页函数。
 * 当列表长度变化导致当前页越界时，自动回落到最后一页。
 */
export function usePagination(listRef, pageSize = 5) {
  const page = ref(1);
  const total = computed(() => Math.max(1, Math.ceil((listRef.value?.length ?? 0) / pageSize)));
  const paged = computed(() => (listRef.value ?? []).slice((page.value - 1) * pageSize, page.value * pageSize));

  watch(total, (t) => {
    if (page.value > t) page.value = t;
  });

  const go = (n) => {
    page.value = Math.min(Math.max(1, n), total.value);
  };

  return { page, total, paged, go };
}
