import http from '@/utils/request'

export interface SexRatio {
  date: string
  sexRatio: string
}

export const sexRatioApi = {
  getSexRatioList: (params: any) => http.get(`/progress/start`, params),
}