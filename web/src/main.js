import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import App from './App.vue'
import ApplicationsView from './views/ApplicationsView.vue'
import CvsView from './views/CvsView.vue'
import ChatView from './views/ChatView.vue'
import ProfileView from './views/ProfileView.vue'
import ExclusionsView from './views/ExclusionsView.vue'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', redirect: '/applications' },
    { path: '/applications', component: ApplicationsView },
    { path: '/cvs', component: CvsView },
    { path: '/chat', component: ChatView },
    { path: '/profile', component: ProfileView },
    { path: '/exclusions', component: ExclusionsView },
  ],
})

const vuetify = createVuetify({ components, directives })

createApp(App).use(router).use(vuetify).mount('#app')
