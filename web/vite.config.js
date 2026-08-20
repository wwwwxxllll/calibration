import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

// 后端 FastAPI 默认监听 http://127.0.0.1:8000
const BACKEND = 'http://127.0.0.1:8000';

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      // 前端同源请求，转发到后端
      '/state': BACKEND,
      '/agents': BACKEND,
      '/tools': BACKEND,
      '/actions': BACKEND,
      '/calibrations': BACKEND,
      '/files': BACKEND
    }
  }
});
