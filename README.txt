AI视频字幕生成播放器

通过调用千问大模型生成AI视频，通过提示词生成字幕，最后通过 Dplayer 播放视频和加载字幕。

开发环境（环境非常重要）：
  1. python 3.11.1
  2. node 20.11.0
  
目录说明：
  -- mywebsite 主应用目录
  -- progress 应用目录
  -- web 前端项目
  -- manage.py 后端入口文件
  -- requirements.txt 依赖列表
  
启动步骤：
  1. 安装 node
  2. 安装 pnpm，这个使用 node 的命令安装，任意目录下执行终端命令：
     ```sh
     npm install -g pnpm
     ```
  3. 安装前端项目依赖，终端进入前端项目根目录 web 文件夹，执行终端命令：
     ```sh
     pnpm install
     ```
  4. 切换 python 版本到 3.11.1，进入后端项目根目录 mywebsite 文件夹，执行终端命令：
     ```sh
     pip install -r requirements.txt
     ```
  5. 启动后端，在 zimuku 文件夹下执行终端命令：
     ```sh
     python manage.py runserver
     ```
  6. 启动前端，在 web 文件夹下执行终端命令：
     ```sh
     pnpm dev
     ```
