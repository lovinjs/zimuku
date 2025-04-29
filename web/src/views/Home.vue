<script lang="ts" setup>
import {ref, onMounted, computed} from 'vue'
import {sexRatioApi} from '@/api/sexRatio'
import {ElMessage, type UploadFile} from 'element-plus'
import DPlayer, {type DPlayerOptions} from 'dplayer'
import dayjs from 'dayjs'
import utc from "dayjs/plugin/utc";

dayjs.extend(utc);

const fileName = ref('')
const uploadFileName = ref('')
const isProcessing = ref(false)
const processProgress = ref(0)
const processStatus = ref('')
const startTime = ref(0)
const elapsedTime = ref(0)
let animationFrameId: any = null
const logs = ref<string[]>([])
const isQuerying = ref(false)
const queryDate = ref('')
const zimukuVideoUrl = ref('')
const zimukuVideoFilename = ref('')


const formattedTime = computed(() => {
  return dayjs(elapsedTime.value).utc().format("mm:ss:SSS")
})

const updateTimer = () => {
  elapsedTime.value = dayjs().valueOf() - startTime.value
  animationFrameId = requestAnimationFrame(updateTimer)
}

const startTimer = () => {
  startTime.value = dayjs().valueOf()
  updateTimer()
}

const stopTimer = () => {
  cancelAnimationFrame(animationFrameId)
}

const socket = new WebSocket('ws://127.0.0.1:8000/ws/socket-server/')

socket.onopen = function (event) {
  console.log('socket 连接已建立')
  socket.send(JSON.stringify({type: 'heart', content: "heart beat"}))
  setInterval(() => {
    socket.send(JSON.stringify({type: 'heart', content: "heart beat"}))
  }, 30000)
}

socket.onmessage = function (event) {
  const data = JSON.parse(event.data)
  const content = data.content
  const file = data.file
  console.log('收到 socket 消息:', content)
  if (content === 'heart beat') return
  const log = `[${dayjs().format("HH:mm:ss")}] ${content}`
  processProgress.value += 5.6
  logs.value.push(log)
  if (file) {
    zimukuVideoUrl.value = import.meta.env.VITE_BASE_URL + `/static/${file}`
    zimukuVideoFilename.value = file
  }
  if (processProgress.value >= 100) {
    isProcessing.value = false
    processStatus.value = 'success'
    stopTimer()
    logs.value.push(`[${new Date().toLocaleTimeString()}] 处理完成！`)
  }
}

socket.onclose = function (event) {
  console.log('socket 连接已关闭')
}

socket.onerror = function (error) {
  console.error('socket 发生错误:', error)
}

const queryResults = ref<any>([])

const handleFileChange = (file: UploadFile) => {
  fileName.value = file.name
}

const beforeUpload = (file: any) => {
  const isLt10M = file.size / 1024 / 1024 < 10
  if (!isLt10M) {
    ElMessage.error('上传文件大小不能超过10MB!')
  }
  return isLt10M
}

const handleSuccess = (response: any, file: any) => {
  uploadFileName.value = response.full_path
  ElMessage.success('文件上传成功')
}

const handleError = (err: any) => {
  ElMessage.error('文件上传失败')
  console.error(err)
}

const startProcess = () => {
  if (!uploadFileName.value) {
    ElMessage.warning('请先上传文件！')
    return
  }
  isProcessing.value = true
  processProgress.value = 0
  logs.value = []
  startTimer()
  socket.send(JSON.stringify({type: 'startProcess', content: uploadFileName.value}))
}

interface Props {
  videoUrl: string
  danmakuApi?: string
  autoplay?: boolean
}


const dplayerRef = ref<HTMLDivElement | null>(null)
let dp: DPlayer | null = null


const initPlayer = () => {
  if (!zimukuVideoUrl.value) return

  const options: DPlayerOptions = {
    container: document.getElementById('dplayer'),
    video: {
      url: zimukuVideoUrl.value,
    },
    autoplay: false,
    danmaku: {
      id: zimukuVideoFilename.value,
      api: 'http://127.0.0.1:8000/progress/start/',
    }
  }


  if (dp) {
    dp.destroy()
    dp = null
  }

  dp = new DPlayer(options)

  console.log('播放器已创建')

  dp.on('play', () => {
    console.log('视频开始播放')
  })

  dp.on('danmaku_show', () => {
    console.log('弹幕显示')
  })
}

const playVideo = () => {
  console.log('播放视频')
  initPlayer()
}

onMounted(() => {
  initPlayer()
})

onBeforeUnmount(() => {
  if (dp) {
    dp.destroy()
  }
})
</script>

<template>
  <div class="min-h-screen bg-gray-50 p-8 bg">
    <div class="mx-auto max-w-7xl space-y-8">
      <h1 class="text-3xl font-bold text-gray-900 mb-8 text-center">千问大模型视频弹幕生成系统</h1>
      <!-- 文件上传区 -->
      <div class="rounded-lg bg-white p-6 shadow-xl">
        <h2 class="mb-6 text-xl font-medium text-dark-800">视频文件上传</h2>
        <div class="flex items-center gap-4">
          <el-upload
              class="upload-demo"
              action="/api/upload/"
              accept=".mp4"
              :on-success="handleSuccess"
              :on-error="handleError"
              :before-upload="beforeUpload"
              :on-change="handleFileChange"
              :limit="1"
          >
            <el-button type="primary" class="!rounded-button">选择文件</el-button>
          </el-upload>
          <span v-if="fileName" class="text-gray-600">已选择: {{ fileName }}</span>
          <el-button type="success" :loading="isProcessing" @click="startProcess"
                     class="ml-auto !rounded-button whitespace-nowrap">
            开始运行
          </el-button>
        </div>
      </div>

      <!-- 运行状态区 -->
      <div class="rounded-lg bg-white p-6 shadow-xl">
        <h2 class="mb-6 text-xl font-medium text-dark-800">运行状态 [ {{ formattedTime }} ]</h2>
        <el-progress :percentage="processProgress" :status="processStatus" class="mb-4 w-full"/>
        <div class="h-60 overflow-y-auto rounded border border-lime-700 bg-black p-4 font-mono">
          <div v-for="(log, index) in logs" :key="index" class="text-sm">
            <span class="text-lime-400">{{ log }}</span>
          </div>
        </div>
      </div>

      <!-- 结果展示区 -->
      <div class="grid grid-cols-1 gap-6">
        <div class="rounded-lg bg-white p-6 shadow-xl h-128">
          <div class="flex justify-between">
            <h2 class="mb-6 text-xl font-medium text-dark-800">视频弹幕预览</h2>
             <el-button type="success" @click="playVideo"
                     class="ml-auto !rounded-button whitespace-nowrap">
              预览视频
            </el-button>
          </div>
          <div class="w-full" v-if="zimukuVideoUrl">
            <div id="dplayer" class="dplayer-container"></div>
          </div>
          <div v-else>
            <el-empty description="暂无视频弹幕生成"></el-empty>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.bg {
  background: url('../assets/img/bg1.jpg') no-repeat center center/cover;
}

.upload-demo {
  display: inline-block;
}

.dplayer-container {
  width: 800px;
  height: 400px;
  margin: 0 auto;
}
</style>
