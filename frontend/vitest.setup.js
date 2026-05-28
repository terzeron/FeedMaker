import { enableAutoUnmount } from '@vue/test-utils';
import { afterEach, vi } from 'vitest';

globalThis.jest = vi;
enableAutoUnmount(afterEach);
