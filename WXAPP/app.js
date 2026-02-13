// app.js
App({
  onLaunch() {
    // 初始化本地存储中的用户数据
    const userData = wx.getStorageSync('userData') || {
      nickname: '游客',
      likeCount: 0
    };
    wx.setStorageSync('userData', userData);
  },
  
  globalData: {
    userInfo: null
  }
});
