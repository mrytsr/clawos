# WXAPP - 点赞助手小程序

## 项目结构

```
WXAPP/
├── app.js              # 应用入口
├── app.json            # 应用配置
├── app.wxss            # 全局样式
├── sitemap.json        # 索引配置
├── pages/
│   ├── index/         # 首页（点赞功能）
│   │   ├── index.js
│   │   ├── index.json
│   │   ├── index.wxml
│   │   └── index.wxss
│   └── my/            # 我的页面
│       ├── my.js
│       ├── my.json
│       ├── my.wxml
│       └── my.wxss
└── images/            # 图片资源
    ├── home.png
    ├── home-active.png
    ├── my.png
    └── my-active.png
```

## 功能说明

### 首页
- 点赞按钮：点击可以点赞/取消点赞
- 点赞计数：显示当前点赞总数
- 数据持久化：点赞状态保存在本地存储

### 我的页面
- 用户头像：显示昵称首字母
- 昵称编辑：点击可修改昵称
- 关于入口：查看小程序信息

## 使用方法

1. 在微信开发者工具中导入项目
2. 选择项目目录为 `WXAPP`
3. 点击"预览"生成二维码
4. 用微信扫描二维码体验

## 预览命令

```bash
node preview.js ./WXAPP ./preview-qrcode.png 1
```

## 注意事项

- tabBar 图标需要真实的 PNG 图片，请放入 `images/` 目录
- 如需真实图标，建议尺寸: 81x81px
