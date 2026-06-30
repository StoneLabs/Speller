import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import { initConfig } from './composables/useConfig.js'

await initConfig()
createApp(App).mount('#app')
