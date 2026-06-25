<template>
  <img
    v-if="visible"
    :src="currentSrc"
    :alt="alt"
    :class="imgClass"
    :style="style"
    loading="lazy"
    @error="onError"
  />
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

type Fit = 'cover' | 'contain'

const props = withDefaults(
  defineProps<{
    src?: string
    alt: string
    bodyPart?: string
    fit?: Fit
    /**
     * true: 默认先走后端代理 /api/exercises/proxy-image
     * false: 先直连外网图片，失败再切换代理
     */
    preferProxy?: boolean
    class?: string
  }>(),
  {
    src: '',
    bodyPart: '',
    fit: 'contain',
    preferProxy: true,
    class: ''
  }
)

const triedProxy = ref(false)
const visible = ref(true)

function isHttpUrl(url: string) {
  return /^https?:\/\//i.test(url)
}

function toProxy(url: string) {
  // Electron file:// 下，`/api/...` 会解析为 `file:///api/...`，必须拼接完整 http 地址
  if (typeof window !== 'undefined' && window.location?.protocol === 'file:') {
    const port =
      (window as any).__BACKEND_PORT__ ||
      localStorage.getItem('__BACKEND_PORT__') ||
      new URLSearchParams(window.location.search).get('backendPort') ||
      '8000'
    return `http://127.0.0.1:${port}/api/exercises/proxy-image?url=${encodeURIComponent(url)}`
  }
  return `/api/exercises/proxy-image?url=${encodeURIComponent(url)}`
}

function toElectronAbsolutePath(pathname: string) {
  if (!pathname || !pathname.startsWith('/')) {
    return pathname
  }
  if (typeof window !== 'undefined' && window.location?.protocol === 'file:') {
    const port =
      (window as any).__BACKEND_PORT__ ||
      localStorage.getItem('__BACKEND_PORT__') ||
      new URLSearchParams(window.location.search).get('backendPort') ||
      '8000'
    return `http://127.0.0.1:${port}${pathname}`
  }
  return pathname
}

const rawSrc = computed(() => String(props.src || ''))

const currentSrc = computed(() => {
  if (!rawSrc.value) return ''
  // preferProxy：先走代理；代理失败(onError)后，尝试直连原始 URL（若仍失败再占位）
  if (props.preferProxy && isHttpUrl(rawSrc.value)) {
    return triedProxy.value ? rawSrc.value : toProxy(rawSrc.value)
  }
  // 非 preferProxy：先直连；失败后切到代理
  if (triedProxy.value && isHttpUrl(rawSrc.value)) {
    return toProxy(rawSrc.value)
  }
  // 后端可能返回 /api/... 相对路径；Electron file:// 下需要转成 http://127.0.0.1:{port}/api/...
  return toElectronAbsolutePath(rawSrc.value)
})

const style = computed(() => ({
  objectFit: props.fit
}))

const imgClass = computed(() => props.class)

function onError() {
  if (!rawSrc.value) {
    visible.value = false
    return
  }

  if (props.preferProxy && !triedProxy.value && isHttpUrl(rawSrc.value)) {
    // 代理失败，退回直连原始 URL
    triedProxy.value = true
    return
  }
  if (!triedProxy.value && isHttpUrl(rawSrc.value) && !props.preferProxy) {
    triedProxy.value = true
    return
  }
  // Don't show placeholder; hide the image area.
  visible.value = false
}

watch(
  () => props.src,
  () => {
    triedProxy.value = false
    visible.value = true
  }
)
</script>
