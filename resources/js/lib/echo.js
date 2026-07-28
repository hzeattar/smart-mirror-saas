import Echo from 'laravel-echo'
import Pusher from 'pusher-js'

export function createEcho() {
  const key = import.meta.env.VITE_REVERB_APP_KEY || import.meta.env.VITE_PUSHER_APP_KEY
  if (!key) return null

  window.Pusher = Pusher
  const token = localStorage.getItem('smart_mirror_token')
  return new Echo({
    broadcaster: 'reverb',
    key,
    wsHost: import.meta.env.VITE_REVERB_HOST || window.location.hostname,
    wsPort: Number(import.meta.env.VITE_REVERB_PORT || 80),
    wssPort: Number(import.meta.env.VITE_REVERB_PORT || 443),
    forceTLS: (import.meta.env.VITE_REVERB_SCHEME || 'https') === 'https',
    enabledTransports: ['ws', 'wss'],
    authEndpoint: '/api/broadcasting/auth',
    auth: { headers: { Authorization: `Bearer ${token}`, Accept: 'application/json' } },
  })
}
