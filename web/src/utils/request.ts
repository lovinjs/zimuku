import axios, { type AxiosInstance, type AxiosRequestConfig, type AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'

interface ApiResponse<T = any> {
  msg: string
  code: number
  data: T
}

class HttpRequest {
  private instance: AxiosInstance
  private readonly options: AxiosRequestConfig

  constructor(options: AxiosRequestConfig = {}) {
    this.options = options
    this.instance = axios.create(options)
    this.setupInterceptors()
  }

  // 拦截器配置
  private setupInterceptors() {
    // 请求拦截
    this.instance.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('token')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )
    // 响应拦截
    this.instance.interceptors.response.use(
      (response: AxiosResponse<any>) => {
        const { data } = response
        if (data.code !== 200) {
          ElMessage.error(data.msg || '请求失败')
          return Promise.reject(data)
        }
        return data
      },
      (error) => {
        ElMessage.error(error.response?.data?.message || '服务异常')
        return Promise.reject(error)
      }
    )
  }

  // 通用请求方法
  request<T = any>(config: AxiosRequestConfig): Promise<T> {
    return this.instance.request(config)
  }

  get<T = any>(url: string, params?: any, config?: AxiosRequestConfig): Promise<T> {
    return this.instance.get(url, { ...config, params })
  }

  post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return this.instance.post(url, data, config)
  }

  put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return this.instance.put(url, data, config)
  }

  delete<T = any>(url: string, params?: any, config?: AxiosRequestConfig): Promise<T> {
    return this.instance.delete(url, { ...config, params })
  }

  upload<T = any>(url: string, file: File, config?: AxiosRequestConfig) {
    const formData = new FormData()
    formData.append('file', file)
    return this.post<T>(url, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      ...config
    })
  }
}

// 创建实例并配置基础参数
const http = new HttpRequest({
  baseURL: import.meta.env.VITE_API_BASEURL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json;charset=UTF-8'
  }
})

export default http