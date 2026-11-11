import {tick} from 'svelte';
import {get, writable} from 'svelte/store';

/** Browser-only responsive state; it never opens a native window or reads product data. */
export function createBrowserSidebar() {
  const state = writable({narrow: false, open: false});
  const focus = (selector: string) => document.querySelector<HTMLButtonElement>(selector)?.focus();
  return {
    subscribe: state.subscribe,
    start() {
      const media = matchMedia('(max-width: 959px)');
      const update = () => state.set({narrow: media.matches, open: false});
      update();
      media.addEventListener('change', update);
      return () => media.removeEventListener('change', update);
    },
    async open() {
      if (!get(state).narrow) return;
      state.update(value => ({...value, open: true}));
      await tick();
      focus('.browser-client .sidebar-titlebar .icon-button');
    },
    close(restoreFocus = true) {
      if (!get(state).open) return;
      state.update(value => ({...value, open: false}));
      if (restoreFocus) void tick().then(() => focus('.browser-client .browser-sidebar-toggle'));
    },
  };
}
