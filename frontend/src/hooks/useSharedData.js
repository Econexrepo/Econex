import { useQuery } from '@tanstack/react-query'
import api from '../api/axios'

export function useDashboardStats() {
  return useQuery({
    queryKey: ['dashboard', 'stats'],
    queryFn: () => api.get('/api/dashboard/stats').then(res => res.data),
  })
}

export function useRSUITrend() {
  return useQuery({
    queryKey: ['dashboard', 'rsui-trend'],
    queryFn: () => api.get('/api/dashboard/rsui-trend').then(res => res.data),
  })
}
