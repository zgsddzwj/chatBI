import { useRef, useCallback, useState, useEffect } from "react";

interface VirtualListOptions {
  itemHeight: number;
  overscan?: number;
}

interface VirtualListState {
  startIndex: number;
  endIndex: number;
  virtualItems: { index: number; style: React.CSSProperties }[];
  totalHeight: number;
  scrollToIndex?: (index: number) => void;
}

/**
 * 虚拟列表 Hook
 * 用于长列表性能优化，只渲染可视区域内的元素
 */
export function useVirtualList<T>(
  items: T[],
  containerRef: React.RefObject<HTMLElement | null>,
  options: VirtualListOptions
): VirtualListState {
  const { itemHeight, overscan = 3 } = options;
  const [scrollTop, setScrollTop] = useState(0);
  const [containerHeight, setContainerHeight] = useState(0);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const update = () => {
      setScrollTop(el.scrollTop);
      setContainerHeight(el.clientHeight);
    };

    update();
    el.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);

    return () => {
      el.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, [containerRef]);

  const totalHeight = items.length * itemHeight;
  const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
  const visibleCount = Math.ceil(containerHeight / itemHeight) + overscan * 2;
  const endIndex = Math.min(items.length - 1, startIndex + visibleCount);

  const virtualItems = [];
  for (let i = startIndex; i <= endIndex; i++) {
    virtualItems.push({
      index: i,
      style: {
        position: "absolute" as const,
        top: i * itemHeight,
        left: 0,
        right: 0,
        height: itemHeight,
      },
    });
  }

  const scrollToIndex = useCallback(
    (index: number) => {
      const el = containerRef.current;
      if (!el) return;
      el.scrollTop = index * itemHeight;
    },
    [containerRef, itemHeight]
  );

  return {
    startIndex,
    endIndex,
    virtualItems,
    totalHeight,
    scrollToIndex,
  };
}
