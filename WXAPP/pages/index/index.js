// pages/index/index.js
Page({
  data: {
    isLiked: false,
    likeCount: 0
  },

  onLoad() {
    // 获取存储的点赞状态
    const userData = wx.getStorageSync('userData') || {};
    this.setData({
      isLiked: userData.isLiked || false,
      likeCount: userData.likeCount || 0
    });
  },

  handleLike() {
    const newLiked = !this.data.isLiked;
    const newCount = newLiked 
      ? this.data.likeCount + 1 
      : Math.max(0, this.data.likeCount - 1);
    
    this.setData({
      isLiked: newLiked,
      likeCount: newCount
    });
    
    // 保存到本地存储
    const userData = wx.getStorageSync('userData') || {};
    userData.isLiked = newLiked;
    userData.likeCount = newCount;
    wx.setStorageSync('userData', userData);
    
    // 提示
    wx.showToast({
      title: newLiked ? '点赞成功' : '取消点赞',
      icon: 'success'
    });
  }
});
