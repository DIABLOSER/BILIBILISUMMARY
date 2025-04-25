<template>
  <div class="video-detail">
    <div class="video-container">
      <!-- 视频播放器 -->
      <div class="video-player">
        <div class="video-header">
          <img :src="proxyImage(video.owner.face)" alt="作者头像" class="author-avatar" />
          <span class="author-name">{{ video.owner.name }}</span>
        </div>
        <h1 class="video-title">{{ video.title }}</h1>
        <video class="videoView" :src="proxyVideoUrl" controls width="100%" :muted="false" autoplay></video>
      </div>

      <!-- 摘要 -->
      <div class="summary-container">
        <div class="summary-header">
          <h2>视频摘要</h2>
          <button class="save-btn" @click="saveSummary" v-if="renderedSummary">保存文档</button>
        </div>
        <div class="summary-section" v-html="renderedSummary"></div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import MarkdownIt from "markdown-it"; // 替换 vue-markdown
import { useRouter } from 'vue-router';
import { useStore } from 'vuex';
import { computed } from 'vue';
const md = new MarkdownIt(); // 初始化 markdown-it 实例

export default {
  name: 'VideoDetail',
  setup(){
    const router = useRouter();
    const store = useStore();
    const userInfo = computed(() => store.getters.userInfo);
    return {
      userInfo,
      router // 返回 router 对象以便在模板中使用
      
    };
  },
  data() {
    return {
      video: {},
      commentData: [],
      commentPage: 1,
      commentHasMore: true,
      commentLoading: false,
      userId: this.userInfo.mid, // 假设用户登录后存储了userId
      summary: {},
      renderedSummary: "" // 新增字段用于存储渲染后的 Markdown 内容
    };
  },
  computed: {
    proxyVideoUrl() {
      if (!this.video.playurl) return '';
      const playurl = this.video.playurl.startsWith('http') ? this.video.playurl : `https:${this.video.playurl}`;
      return `http://localhost:3000/api/proxy_video?url=${encodeURIComponent(playurl)}`;
    }
  },
  async created() {
    const videoId = this.$route.params.aid;
    await this.fetchVideoDetails(videoId);
  },
  methods: {
    // 获取视频详情
    async fetchVideoDetails(videoId) {
      try {
        const res = await axios.get("http://localhost:3000/api/video_details", {
          params: { aid: videoId },
          withCredentials: true
        });
        if (res.data.code === 0) {
          this.video = res.data.data;
          await this.generateSummary();
        }
      } catch (error) {
        alert("视频详情获取失败");
      }
    },

    // 获取摘要
    async generateSummary() {
      try {
        const videoId = this.video.bvid;
        const response = await axios.post("http://localhost:3000/api/video_summary", {
          bvid: videoId
        }, {
          params: { bvid: videoId },
          withCredentials: true,
          headers: {
            'Cookie': document.cookie // 新增请求头
          },
          timeout: 30000 // 增加超时时间到 30 秒
        });
      
        if (response && response.data && response.data.code === 0) {
          this.summary = response.data.data;
          // 使用 markdown-it 渲染摘要内容
          console.log("摘要数据"+this.summary.summary);
          this.renderedSummary = md.render(this.summary.summary);
        } else {
          console.error("生成总结失败：", response ? response.data.message : "未知错误");
          alert("生成总结失败：" + (response ? response.data.message : "未知错误"));
        }
      } catch (error) {
        console.error("生成总结时发生错误：", error);
        if (error.response) {
          // 服务器响应但状态码不是 2xx
          console.error("服务器响应错误：", error.response.status, error.response.data);
          alert("生成总结失败：" + error.response.data.message);
        } else if (error.request) {
          // 请求已发出但没有收到响应
          console.error("请求未收到响应：", error.request);
          alert("请求未收到响应，请检查网络连接");
        } else {
          // 发生在设置请求时的错误
          console.error("请求设置错误：", error.message);
          alert("请求设置错误：" + error.message);
        }
      }
    },

    // 保存文档摘要
    async saveSummary() {
      try {
        if (!this.userId) {
          alert("请先登录");
          return;
        }

        if (!this.summary || !this.summary.summary) {
          alert("没有可保存的摘要内容");
          return;
        }

        const response = await axios.post("http://localhost:3000/api/save_summary", {
          user_id: this.userId,
          video_id: this.video.bvid,
          summary_text: this.summary.summary  // 确保字段名与后端一致
        });

        if (response.data.code === 0) {
          alert("文档保存成功");
        } else {
          alert("保存失败：" + response.data.message);
        }
      } catch (error) {
        console.error("保存文档时发生错误：", error);
        if (error.response) {
          // 服务器响应但状态码不是 2xx
          console.error("服务器响应错误：", error.response.status, error.response.data);
          alert("保存失败：" + error.response.data.message);
        } else if (error.request) {
          // 请求已发出但没有收到响应
          console.error("请求未收到响应：", error.request);
          alert("请求未收到响应，请检查网络连接");
        } else {
          // 发生在设置请求时的错误
          console.error("请求设置错误：", error.message);
          alert("请求设置错误：" + error.message);
        }
      }
    },

    // 代理图片地址
    proxyImage(url) {
      return `http://localhost:3000/api/proxy_image?url=${encodeURIComponent(url)}`;
    },

    // 格式化时间戳
    formatTime(timestamp) {
      return new Date(timestamp * 1000).toLocaleString();
    }
  }
};
</script>

<style scoped>
.video-detail {
  padding: 10px;
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  height: 100vh; /* 设置高度为视口高度 */
}

.video-container {
  display: flex;
  /* gap: 20px; */
  flex: 1; /* 占据剩余空间 */
  overflow: hidden; /* 禁止外部滚动 */
}
.analyse{
  margin-right: 0;
  margin-left: auto;
}

.video-player {
  flex: 1;
  max-height: 100%; /* 限制视频区域的最大高度 */
  overflow: hidden; /* 禁止视频区域滚动 */
}

.video-header {
  display: flex;
  align-items: center;
  margin-bottom: 5px;
}

.author-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  margin-right: 12px;
}

.author-name {
  font-size: 18px;
  font-weight: 500;
  color: #fa7298;
}

.video-title {
  font-weight: 500;
  font-size: 20px;
  /* padding-top: 10px;*/
  padding-bottom: 8px; 
  color: #1a1a1a;
}

.description {
  font-size: 14px;
  color: black;
  line-height: 1.6;
  
}
.videoView{
  width: 100%;
  aspect-ratio: 668 / 376;
}

.dynamic-fields {
  margin-top: 20px;
  padding: 10px;
  background-color: #f9f9f9;
  border-radius: 4px;
}

.field-item {
  margin-bottom: 10px;
  font-size: 14px;
}

.field-item strong {
  font-weight: bold;
  color: #333;
}

.summary-container {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.summary-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  padding: 0 10px;
}

.save-btn {
  background-color: #00a1d6;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.3s;
}

.save-btn:hover {
  background-color: #0091c2;
}

.summary-section {
  flex: 1;
  overflow-y: auto;
  scrollbar-width: thin; /* 美化滚动条 */
  scrollbar-color: rgba(0, 0, 0, 0.2) transparent; /* 滚动条颜色 */
  padding: 10px;
}

.summary-section h2 {
  font-size: 18px;
  font-weight: bold;
  margin-bottom: 10px;
}

.summary-section li {
  margin-bottom: 5px;
}

.summary-section .tag {
  display: inline-block;
  background-color: #fff;
  color: #fa7298;
  padding: 2px 5px;
  border-radius: 3px;
  margin-right: 5px;
}

.summary-section::-webkit-scrollbar {
  width: 8px; /* 滚动条宽度 */
}

.summary-section::-webkit-scrollbar-track {
  background: transparent; /* 滚动条背景透明 */
}

.summary-section::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.2); /* 滚动条颜色 */
  border-radius: 4px; /* 滚动条圆角 */
}



.user-info {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  margin-right: 12px;
}

.username {
  font-weight: 500;
  color: #2d2d2d;
}

.content {
  color: #333;
  line-height: 1.6;
  margin-bottom: 10px;
}

.meta {
  display: flex;
  justify-content: space-between;
  color: #666;
  font-size: 0.9em;
}

.likes::before {
  content: '👍 ';
}

.no-comments {
  text-align: center;
  color: #999;
  padding: 30px;
}
</style>