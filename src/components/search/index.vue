<template>
  <div class="search-container">
    <div class="content" @scroll="handleScroll">
      <div class="video-grid">
        <div v-for="(video, index) in  videoData" :key="index" class="video-item" @click="navigateToVideo(video.aid)">
          <img :src="`http://localhost:3000/api/proxy_image?url=${encodeURIComponent(`http:` + video.pic)}`" :alt="video.title" class="video-thumbnail" />
          <!-- <h2>{{ video.title }}</h2> -->
          <h2 v-html="highlightTitle(video.title)"></h2>
        </div>
      </div>
      <div v-if="loading" class="loading-more">加载中...</div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import { API_ENDPOINTS } from '@/config/api';

export default {
  name: 'Search',
  data() {
    return {
      searchKeyword: this.$route.params.keyword,
      videoData: [],
      loading: false,
      page: 1,
      hasMore: true
    };
  },
  watch: {
    keyword(newKeyword) {
      this.searchKeyword = newKeyword;
      this.searchVideos();
    }
  },
  methods: {
    highlightTitle(title) {
    // 去除原始 <em class="keyword"> 标签
    const temp = document.createElement("div");
    temp.innerHTML = title;
    const cleanText = temp.textContent || temp.innerText || "";

    // 使用关键词重新高亮
    const keyword = this.searchKeyword;
    if (!keyword) return cleanText;

    const escapedKeyword = keyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const regex = new RegExp(escapedKeyword, "gi");

    return cleanText.replace(regex, match => `<span class="keyword">${match}</span>`);

  },
    async searchVideos() {
      console.log("搜索关键词:", this.searchKeyword);
      if(!this.loading){
        this.videoData = [];
        this.page=1;
      }
      try {
        const res = await axios.get(API_ENDPOINTS.SEARCH_VIDEOS, {
          params: { keyword: this.searchKeyword, pn: this.page, ps: 10 },
          withCredentials: true,
          headers: {
            'Cookie': document.cookie
          }
        });
        if (res.data.code === 0) {
          this.videoData = [...this.videoData, ...(res.data.data?.result || [])];
          this.hasMore = res.data.data?.result.length > 0;
        } else {
          alert(res.data.message || "搜索视频失败");
        }
      } catch (error) {
        alert("搜索视频时发生错误"+error);
      } finally {
        this.loading = false;
      }
    },
    navigateToVideo(aid) {
      this.$router.push({ name: 'VideoDetail', params: { aid } });
    },
    handleScroll(event) {
      const { scrollTop, scrollHeight, clientHeight } = event.target;
      if (scrollHeight - scrollTop <= clientHeight + 50 && !this.loading && this.hasMore) {
        this.loading = true;
        this.page += 1;
        this.searchVideos();
      }
    }
  },
  created() {
      this.searchVideos();
  },
};
</script>

<style scoped>
.search-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
  height: 100vh;
  display: flex;
  flex-direction: column;
}


.content {
  flex: 1;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 0, 0, 0.2) transparent;
}

.content::-webkit-scrollbar {
  width: 8px;
}

.content::-webkit-scrollbar-track {
  background: transparent;
}

.content::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.2);
  border-radius: 4px;
}

.video-grid {
  display: flex;
  flex-wrap: wrap;
  /* gap: 20px; */
  
}

.video-item {
  flex: 0 0 calc(25%);
  width: 100%;
  aspect-ratio: 240 / 208;
  /* border: 1px solid #ddd; */
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  position: relative;
  cursor: pointer;
  padding: 10px;
  
}

.video-item .video-thumbnail {
  aspect-ratio: 240 / 135;
  width: 100%;
  object-fit: cover;
  margin-bottom: 10px;
  border-radius: 4px;
}

.video-item h2 {
  width: 100%;
  font-size: 16px;
  margin-bottom: 10px;
  color: black;
  white-space: normal;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  text-overflow: ellipsis;
  font-weight: 500; /* 加粗字体 */
}
.loading-more {
  text-align: center;
  padding: 10px;
  color: #666;
}
::v-deep .keyword {
  color: #FA7298;
  font-size: 16px;
  font-weight: 500;
}

</style>