// API基础URL
export const API_BASE_URL = 'http://localhost:3000/api';

export const API_ENDPOINTS = {
  // 获取登录二维码
  GET_QR_CODE: `${API_BASE_URL}/get_qr_code`,
  // 检查二维码状态
  CHECK_QR_CODE: `${API_BASE_URL}/check_qr_code`,
  // 获取用户信息
  USER_INFO: `${API_BASE_URL}/user_info`,
  // 获取视频详情
  VIDEO_DETAILS: `${API_BASE_URL}/video_details`,
  // 获取视频评论
  VIDEO_COMMENTS: `${API_BASE_URL}/video_comments`,
  // 收藏视频
  COLLECT_VIDEO: `${API_BASE_URL}/collect_video`,
  // 生成视频总结
  VIDEO_SUMMARY: `${API_BASE_URL}/video_summary`,
  // 保存视频总结
  SAVE_SUMMARY: `${API_BASE_URL}/save_summary`,
  // 获取用户保存的视频总结列表
  GET_SUMMARIES: `${API_BASE_URL}/get_summaries`,
  // 删除用户保存的视频总结
  DELETE_SUMMARY: `${API_BASE_URL}/delete_summary`,
  // 更新用户保存的视频总结
  UPDATE_SUMMARY: `${API_BASE_URL}/update_summary`,
  // 获取用户视频列表
  USER_VIDEOS: `${API_BASE_URL}/user_videos`,
  // 搜索视频
  SEARCH_VIDEOS: `${API_BASE_URL}/search_videos`,
  // 获取推荐视频
  RECOMMENDED_VIDEOS: `${API_BASE_URL}/recommended_videos`,
  // 代理图片请求
  PROXY_IMAGE: `${API_BASE_URL}/proxy_image`,
  // 代理视频请求
  PROXY_VIDEO: `${API_BASE_URL}/proxy_video`,
  // 获取文档内容
  GET_SUMMARY_CONTENT: `${API_BASE_URL}/get_summary_content`,
  // 文档分类
  CLASSIFY_DOCUMENTS: `${API_BASE_URL}/classify_documents`,
  // 查看文档
  VIEW_DOCUMENT: `${API_BASE_URL}/view_document`,
  // 更新文档分类
  UPDATE_DOCUMENT_CATEGORY: `${API_BASE_URL}/update_document_category`
};