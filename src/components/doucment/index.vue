<template>
  <div class="document-management">
    <div class="sidebar">
      <h2>文档目录</h2>
      <!-- 搜索框 -->
      <div class="search-box">
        <input 
          type="text" 
          v-model="searchQuery" 
          placeholder="搜索文档..."
          @input="searchSummaries"
        />
      </div>
      <!-- 分类列表 -->
      <ul class="category-list">
        <li 
          v-for="category in categories" 
          :key="category" 
          @click="filterByCategory(category)"
          :class="{ active: selectedCategory === category }"
        >
          {{ category }}
        </li>
      </ul>
      <!-- 动态生成分类下的文档 -->
      <ul>
        <li v-for="summary in filteredSummaries" :key="summary.video_id">
          <div class="summary-item">
            <span @click="openSummary(summary)">
              {{ summary.video_id }} - {{ summary.created_at }}
            </span>
            <div class="summary-actions">
              <button class="edit-btn" @click="editSummary(summary)">编辑</button>
              <button class="delete-btn" @click="deleteSummary(summary.video_id)">删除</button>
            </div>
          </div>
        </li>
      </ul>
    </div>
    <div class="content">
      <div class="content-header">
        <h2>文档内容</h2>
        <div v-if="isEditing" class="edit-actions">
          <button class="save-edit-btn" @click="saveSummaryEdit">保存</button>
          <button class="cancel-edit-btn" @click="cancelEdit">取消</button>
        </div>
      </div>
      <!-- 编辑模式 -->
      <div v-if="isEditing" class="edit-container">
        <textarea v-model="editingSummaryText" class="summary-editor"></textarea>
      </div>
      <!-- 查看模式 -->
      <div v-else class="view-container">
        <pre v-if="renderedSummary" class="document-content" v-html="renderedSummary"></pre>
        <p v-else>请选择一个文档以查看内容。</p>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import { computed } from "vue";
import { useStore } from "vuex";
import { API_ENDPOINTS } from "@/config/api";
import MarkdownIt from "markdown-it"; // 替换 vue-markdown
const md = new MarkdownIt(); // 初始化 markdown-it 实例

export default {
  name: "DocumentManagement",
  setup() {
    const store = useStore();
    const userInfo = computed(() => store.getters.userInfo);
    return {
      userInfo,
    };
  },
  data() {
    return {
      categories: ["全部", "科普", "美妆", "娱乐", "新闻", "游戏"], // 分类数组，添加"全部"选项
      selectedCategory: "全部", // 当前选中的分类
      summaries: [],
      currentDocument: "", // 确保初始值为空字符串
      searchQuery: "", // 搜索关键词
      isEditing: false, // 是否处于编辑模式
      editingSummaryText: "", // 编辑中的文档内容
      editingSummary: null, // 当前编辑的文档对象
      originalSummaries: [], // 保存原始文档列表，用于搜索功能
      renderedSummary: "" // 新增字段用于存储渲染后的 Markdown 内容
    };
  },
  computed: {
    // 根据选中的分类和搜索关键词筛选文档
    filteredSummaries() {
      let filtered = this.summaries;
      
      // 先按分类筛选
      if (this.selectedCategory !== "全部") {
        filtered = filtered.filter(summary => summary.category === this.selectedCategory);
      }
      
      // 再按搜索关键词筛选
      if (this.searchQuery.trim()) {
        const query = this.searchQuery.toLowerCase().trim();
        filtered = filtered.filter(summary => 
          summary.video_id.toLowerCase().includes(query) || 
          summary.summary_text.toLowerCase().includes(query) ||
          summary.created_at.toLowerCase().includes(query)
        );
      }
      
      return filtered;
    },
  },
  async created() {
    await this.fetchSummaries();
    // 获取文档分类
    await this.classifyDocuments();
  },
  methods: {
    // 查询我的文档
    async fetchSummaries() {
      try {
        // 检查 userInfo 是否存在且包含 mid
        if (!this.userInfo || !this.userInfo.mid) {
          alert("请先登录！");
          return this.$router.push("/login");
        }

        const user_id = this.userInfo.mid;
        const response = await axios.get(API_ENDPOINTS.GET_SUMMARIES, {
          params: { user_id },
        });

        if (response.data.code === 0) {
          // 获取文档列表
          const summariesData = response.data.data.summaries;
          
          // 对于每个文档，获取其内容
          for (const summary of summariesData) {
            try {
              // 直接使用数据库中的 summary_text 字段
              summary.summary_text = summary.summary_text || "文档内容为空";
            } catch (err) {
              console.error(`获取文档内容失败: ${err.message}`);
              summary.summary_text = "无法获取文档内容";
            }
          }
          
          this.summaries = summariesData;
          this.originalSummaries = [...this.summaries]; // 保存原始数据用于搜索
          
          // 如果有文档，默认打开第一个
          if (this.summaries.length > 0) {
            console.log("默认打开第一个文档"+this.summaries[0].summary_path);
            this.openSummary(this.summaries[0]);
          }
        } else {
          alert(response.data.message || "获取文档列表失败");
        }
      } catch (error) {
        alert("获取文档列表失败：" + error.message);
      }
    },
    // 打开文档
    async openSummary(summary) {
      console.log("打开文档路径：" + summary.summary_path);

      if (summary) {
        // 直接使用数据库中的 summary_text 字段
        this.currentDocument = summary.summary_text || "文档内容为空";
        this.renderedSummary = md.render(this.currentDocument);
      } else {
        this.currentDocument = "文档内容加载失败";
      }
    },
    async deleteSummary(video_id) {
      if (!confirm("确定要删除该文档吗？")) {
        return;
      }

      try {
        const user_id = this.userInfo.mid;
        const response = await axios.delete(API_ENDPOINTS.DELETE_SUMMARY, {
          data: { user_id, video_id }
        });

        if (response.data.code === 0) {
          alert("文档删除成功");
          await this.fetchSummaries();
        } else {
          alert(response.data.message || "文档删除失败");
        }
      } catch (error) {
        alert("文档删除失败：" + error.message);
      }
    },
    // 根据分类筛选文档
    filterByCategory(category) {
      this.selectedCategory = category;
    },
    
    // 使用KNN算法对文档进行分类
    async classifyDocuments() {
      try {
        if (!this.userInfo || !this.userInfo.mid || this.summaries.length === 0) {
          return;
        }
        
        const user_id = this.userInfo.mid;
        const response = await axios.post(API_ENDPOINTS.CLASSIFY_DOCUMENTS, {}, {
          params: { user_id }
        });
        
        if (response.data.code === 0) {
          const classifiedDocs = response.data.data.classified_documents;
          
          // 更新文档分类信息
          for (const doc of classifiedDocs) {
            const summary = this.summaries.find(s => s.video_id === doc.video_id);
            if (summary) {
              // 根据分类结果设置文档分类
              switch(doc.category) {
                case 0:
                  summary.category = "科普";
                  break;
                case 1:
                  summary.category = "美妆";
                  break;
                case 2:
                  summary.category = "娱乐";
                  break;
                case 3:
                  summary.category = "新闻";
                  break;
                case 4:
                  summary.category = "游戏";
                  break;
                default:
                  summary.category = "其他";
              }
            }
          }
        }
      } catch (error) {
        console.error("文档分类失败：" + error.message);
      }
    },
    
    // 搜索文档
    searchSummaries() {
      // 搜索逻辑已在计算属性中实现
    },
    
    // 编辑文档
    editSummary(summary) {
      this.isEditing = true;
      this.editingSummary = summary;
      this.editingSummaryText = summary.summary_text;
    },
    
    // 保存编辑后的文档
    async saveSummaryEdit() {
      if (!this.editingSummary || !this.editingSummaryText.trim()) {
        alert("文档内容不能为空");
        return;
      }
      
      try {
        const user_id = this.userInfo.mid;
        const response = await axios.put(API_ENDPOINTS.UPDATE_SUMMARY, {
          user_id,
          video_id: this.editingSummary.video_id,
          summary_text: this.editingSummaryText
        });
        
        if (response.data.code === 0) {
          alert("文档更新成功");
          // 更新本地数据
          const index = this.summaries.findIndex(s => s.video_id === this.editingSummary.video_id);
          if (index !== -1) {
            this.summaries[index].summary_text = this.editingSummaryText;
          }
          // 退出编辑模式
          this.cancelEdit();
          // 刷新文档列表
          await this.fetchSummaries();
        } else {
          alert(response.data.message || "文档更新失败");
        }
      } catch (error) {
        alert("文档更新失败：" + error.message);
      }
    },
    
    // 取消编辑
    cancelEdit() {
      this.isEditing = false;
      this.editingSummary = null;
      this.editingSummaryText = "";
    },
  },
};
</script>

<style scoped>
.document-management {
  display: flex;
  height: 100%;
}

.sidebar {
  width: 250px;
  padding: 10px;
  border-right: 1px solid #ccc;
  overflow-y: auto;
}

.content {
  flex: 1;
  padding: 10px;
}

ul {
  list-style-type: none;
  padding: 0;
}

li {
  padding: 8px;
  cursor: pointer;
  border-bottom: 1px solid #eee;
}

li:hover {
  background-color: #f5f5f5;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.delete-btn {
  background-color: #ff4d4f;
  color: white;
  border: none;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
}

.delete-btn:hover {
  background-color: #ff7875;
}

/* 新增分类样式 */
.category-list {
  margin-bottom: 20px;
}

.category-list li {
  padding: 8px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.category-list li:hover {
  background-color: #f0f0f0;
}

.category-list li.active {
  background-color: #e6f7ff;
  color: #1890ff;
  font-weight: bold;
}

/* 搜索框样式 */
.search-box {
  margin-bottom: 15px;
}

.search-box input {
  width: 100%;
  padding: 8px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 14px;
}

.search-box input:focus {
  border-color: #40a9ff;
  outline: none;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}

/* 编辑模式样式 */
.edit-container {
  height: 600px;
  width: 100%;
}

.summary-editor {
  width: 100%;
  height: 100%;
  padding: 10px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 14px;
  line-height: 1.5;
  resize: none;
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.edit-actions {
  display: flex;
  gap: 10px;
}

.save-edit-btn, .cancel-edit-btn {
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  border: none;
}

.save-edit-btn {
  background-color: #1890ff;
  color: white;
}

.save-edit-btn:hover {
  background-color: #40a9ff;
}

.cancel-edit-btn {
  background-color: #f5f5f5;
  color: rgba(0, 0, 0, 0.65);
}

.cancel-edit-btn:hover {
  background-color: #e8e8e8;
}

.summary-actions {
  display: flex;
  gap: 8px;
}

.edit-btn {
  background-color: #1890ff;
  color: white;
  border: none;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
}

.edit-btn:hover {
  background-color: #40a9ff;
}

.category-list li.active {
  background-color: #e6f7ff;
  font-weight: bold;
}

.view-container {
  height: 600px;
  overflow-y: auto;
  padding: 10px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
}

.document-content {
  white-space: pre-wrap;
  /* font-family: monospace;
  line-height: 1.5; */
}
</style>