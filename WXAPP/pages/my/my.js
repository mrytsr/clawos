// pages/my/my.js
Page({
  data: {
    nickname: {
      name: '游客',
      avatar: ''
    },
    tempNickname: '',
    showNicknameModal: false
  },

  onLoad() {
    // 获取存储的用户数据
    const userData = wx.getStorageSync('userData') || {};
    this.setData({
      nickname: {
        name: userData.nickname || '游客',
        avatar: userData.nickname ? userData.nickname.charAt(0).toUpperCase() : ''
      }
    });
  },

  // 编辑昵称
  editNickname() {
    this.setData({
      tempNickname: this.data.nickname.name,
      showNicknameModal: true
    });
  },

  // 昵称输入
  onNicknameInput(e) {
    this.setData({
      tempNickname: e.detail.value
    });
  },

  // 关闭弹窗
  closeModal() {
    this.setData({
      showNicknameModal: false,
      tempNickname: ''
    });
  },

  // 保存昵称
  saveNickname() {
    const newNickname = this.data.tempNickname.trim() || '游客';
    
    // 更新本地存储
    const userData = wx.getStorageSync('userData') || {};
    userData.nickname = newNickname;
    wx.setStorageSync('userData', userData);
    
    // 更新页面显示
    this.setData({
      nickname: {
        name: newNickname,
        avatar: newNickname.charAt(0).toUpperCase()
      },
      showNicknameModal: false,
      tempNickname: ''
    });
    
    wx.showToast({
      title: '修改成功',
      icon: 'success'
    });
  },

  // 跳转到关于页面
  goToAbout() {
    wx.showModal({
      title: '关于点赞助手',
      content: '一个简单的微信小程序Demo\n\n版本: 1.0.0\n\n功能:\n- 首页点赞功能\n- 昵称修改\n- 关于信息',
      showCancel: false,
      confirmText: '知道了',
      confirmColor: '#07c160'
    });
  }
});
