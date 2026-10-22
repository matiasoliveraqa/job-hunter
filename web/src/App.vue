<script setup>
const links = [
  { to: '/applications', icon: 'mdi-briefcase-check', title: 'Postulaciones' },
  { to: '/cvs', icon: 'mdi-file-pdf-box', title: 'CVs' },
  { to: '/chat', icon: 'mdi-robot-happy', title: 'Chat con el agente' },
  { to: '/profile', icon: 'mdi-account-circle', title: 'Mi perfil' },
  { to: '/exclusions', icon: 'mdi-cancel', title: 'Exclusiones' },
]
</script>

<template>
  <v-app>
    <v-navigation-drawer permanent width="230">
      <v-list-item title="Job Hunter" subtitle="Panel local" class="py-4" />
      <v-divider />
      <v-list nav density="comfortable">
        <v-list-item v-for="l in links" :key="l.to" :to="l.to" :prepend-icon="l.icon" :title="l.title" />
      </v-list>
    </v-navigation-drawer>
    <v-main>
      <router-view />
    </v-main>
  </v-app>
</template>
