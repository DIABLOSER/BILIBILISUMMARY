<template>
  <div class="video-collection">
    <div v-if="collectedVideos.length > 0" class="video-list">
      <div v-for="video in collectedVideos" :key="video.video_id" class="video-item">
        <div class="video-thumbnail">
          <img :src="`http://localhost:3000/api/proxy_image?url=${encodeURIComponent(video.cover_url)}`" alt="Video Thumbnail" />
        </div>
        <div class="video-info">
          <h2>{{ video.title || video.video_id }}</h2>
          <!-- <p>{{ video.description || '暂无描述' }}</p> -->
          <button @click="deleteVideo(video.video_id)" class="delete-btn">删除</button>
          <button @click="viewVideoDetails(video.video_id)" class="view-btn">查看详情</button>
        </div>
      </div>
    </div>
    <div v-else class="empty-state">
      <p>暂无收藏视频</p>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { useStore } from 'vuex';
import { useRouter } from 'vue-router';
import axios from 'axios';
import { computed } from 'vue';

export default {
  name: 'Collect',
  setup() {
    const store = useStore();
    const router = useRouter();
    const collectedVideos = ref([]); // 确保初始化为空数组

    // 从 Vuex store 获取用户信息
    const userInfo = computed(() => store.getters.userInfo);

    const fetchCollectedVideos = async () => {
      try {
        const user_id = userInfo.value.mid;  // 修改：直接使用 userInfo.value
        if (!user_id) {
          router.push({ name: 'BilibiliLogin' });
          return;
        }

        const response = await axios.get('http://localhost:3000/api/get_collected_videos', {
          params: { user_id }
        });

        console.log("获取到的收藏视频数据:", response.data.data);
        if (response.data.code === 0) {
          collectedVideos.value = response.data.data.collected_videos || []; // 修改：使用 response.data.data.collected_videos
        }
      } catch (error) {
        console.error('获取收藏视频失败:', error);
      }
    };

    const deleteVideo = async (video_id) => {
      try {
        const user_id = userInfo.value.mid;  // 确保使用 userInfo.value 获取用户 ID
        if (!user_id) {
          alert("请先登录！");
          return router.push({ name: 'BilibiliLogin' });
        }

        const response = await axios.delete('http://localhost:3000/api/delete_collected_video', {
          data: { user_id, video_id }
        });

        if (response.data.code === 0) {
          alert("视频删除成功！");
          await fetchCollectedVideos();  // 删除成功后刷新收藏列表
        } else {
          alert(response.data.message || "视频删除失败");
        }
      } catch (error) {
        console.error('删除收藏视频失败:', error);
        alert("删除收藏视频失败：" + error.message);
      }
    };

    const viewVideoDetails = (video_id) => {
      router.push({ name: 'VideoDetail', params: { aid: video_id } });
    };

    onMounted(() => {
      fetchCollectedVideos();
    });

    return {
      collectedVideos,
      deleteVideo,
      viewVideoDetails,
      userInfo,
    };
  }
};
</script>

<style scoped>
.video-collection {
    padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.video-list {
  /* display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  flex: 1; */
  display: flex;
  flex-wrap: wrap;
  overflow-y: auto;  /* 允许垂直滚动 */
  scrollbar-width: thin;  /* 美化滚动条 */
  scrollbar-color: rgba(0, 0, 0, 0.2) transparent;  /* 滚动条颜色 */
  max-height: 80vh;  /* 设置最大高度为视口的80% */
}

.video-list::-webkit-scrollbar {
  width: 8px;  /* 滚动条宽度 */
}

.video-list::-webkit-scrollbar-track {
  background: transparent;  /* 滚动条背景透明 */
}

.video-list::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.2);  /* 滚动条颜色 */
  border-radius: 4px;  /* 滚动条圆角 */
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

.video-thumbnail img {
    aspect-ratio: 240 / 135;
  width: 100%;
  object-fit: cover;
  margin-bottom: 10px;
  border-radius: 4px;
}

.video-info {
  /* padding: 15px; */
  flex: 1;
  width: 100%;
  display: flex;
  flex-direction: column;
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

.delete-btn {
  margin-top: auto;
  padding: 8px 16px;
  background-color: #ff4d4f;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.delete-btn:hover {
  background-color: #ff7875;
}

.view-btn {
  margin-top: 10px;
  padding: 8px 16px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.view-btn:hover {
  background-color: #45a049;
}

.empty-state {
  text-align: center;
  padding: 50px;
  color: #999;
}
</style>