const ci = require('miniprogram-ci');
const path = require('path');

// 从命令行参数获取项目路径、输出文件名和 robot 编号
const args = process.argv.slice(2);
const projectPath = args[0] || './';
const outputFile = args[1] || './preview-qrcode.png';
const robot = args[2] || '1';  // 默认使用 robot 1

console.log('预览参数:');
console.log('  项目路径:', projectPath);
console.log('  输出文件:', outputFile);
console.log('  Robot编号:', robot);

const project = new ci.Project({
  appid: 'wx36dfd5007f439a12',
  projectPath: projectPath,
  privateKeyPath: './privatekey.key',
});

// 最简配置
ci.preview({
  project,
  desc: '快速预览',
  setting: { es6: true },
  robot: robot,  // 使用传入的 robot 参数
  qrcodeFormat: 'image',
  qrcodeOutputDest: outputFile,
})
.then(result => {
  console.log('预览成功:', outputFile);
  process.exit(0);
})
.catch(err => {
  console.error('预览失败:', err);
  process.exit(1);
});
