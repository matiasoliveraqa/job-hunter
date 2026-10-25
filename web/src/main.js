import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import './style.css'
import App from './App.vue'
import ApplicationsView from './views/ApplicationsView.vue'
import CvsView from './views/CvsView.vue'
import SearchView from './views/SearchView.vue'
import ProfileView from './views/ProfileView.vue'
import ExclusionsView from './views/ExclusionsView.vue'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', redirect: '/search' },
    { path: '/search', component: SearchView },
    { path: '/applications', component: ApplicationsView },
    { path: '/cvs', component: CvsView },
    { path: '/chat', redirect: '/search' },
    { path: '/profile', component: ProfileView },
    { path: '/exclusions', component: ExclusionsView },
  ],
})

const vuetify = createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'dark',
  },
})

createApp(App).use(router).use(vuetify).mount('#app')
