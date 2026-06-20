### AI视频字幕生成播放器

通过调用千问大模型生成AI视频，通过提示词生成字幕，最后通过 Dplayer 播放视频和加载字幕。

#### 1 开发环境

  1. python 3.11.1
  2. node 20.11.0

#### 2 目录说明

- `mywebsite`：主应用目录
- `progress`：应用目录
- `web`：前端项目
- `manage.py`：后端入口文件
- `requirements.txt`：依赖列表

#### 3 启动步骤

  1. 安装 node

  2. 安装 pnpm，在任意目录下执行终端命令：

     ```sh
     npm install -g pnpm
     ```

  3. 安装前端项目依赖，在 web 目录下执行终端命令：

     ```sh
     pnpm install
     ```

  4. 切换 python 版本到 3.11.1，安装 python 依赖，在 mywebsite 目录下执行终端命令：

     ```sh
     pip install -r requirements.txt
     ```

  5. 启动后端项目，在项目根目录下执行终端命令：

     ```sh
     python manage.py runserver
     ```

  6. 启动前端项目，在 web 目录下执行终端命令：

     ```sh
     pnpm dev
     ```
