const fs = require('fs')
const path = require('path')

const distDir = path.join(__dirname, '..', 'dist')
const setups = fs.existsSync(distDir)
  ? fs.readdirSync(distDir).filter((name) => /^FitnessCoach Setup .*\.exe$/i.test(name))
  : []
const setup = setups.sort().pop()
const setupPath = setup ? path.join(distDir, setup) : ''
const unpackedExe = path.join(distDir, 'win-unpacked', 'FitnessCoach.exe')

console.log('')
console.log('========== 桌面版打包完成 ==========')
if (setupPath) {
  console.log(`安装包：${setupPath}`)
}
if (fs.existsSync(unpackedExe)) {
  console.log(`免安装：${unpackedExe}`)
}
console.log('')
console.log('重要：开始菜单/桌面快捷方式里的 FitnessCoach 不会自动更新。')
console.log('请双击上面的「安装包」重新安装，或直接运行「免安装」版。')
console.log('====================================')
console.log('')
