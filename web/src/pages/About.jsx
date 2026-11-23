import { Database, GitBranch, HeartPulse, ScanLine, ShieldCheck } from 'lucide-react'
import { Badge, PageHeading, Panel, TextLink } from '../components/UI.jsx'
import styles from '../styles/Pages.module.css'

export default function About() {
  return <div className={styles.stack}>
    <PageHeading title="项目介绍" description="从 CAMUS 超声心动图研究左心室视频分割与容积估算。" />
    <div className={styles.twoCol}>
      <Panel title="研究背景与目标" className={styles.article}>
        <p>本项目面向处理后的超声心动图，自动分割左室腔并追踪体积变化，用于算法比较、可复现性检查与对团队展示患者级评估过程。</p>
        <div className={styles.articleRow}><ScanLine size={20} /><div><h3>DRA-UNet</h3><p>在 Attention-UNet 上加入空洞残差编码器、ConvLSTM 瓶颈与边缘监督。模型输入为单通道灰度。历史 EchoNet 适配使用灰度复制到三通道。</p></div></div>
        <div className={styles.articleRow}><GitBranch size={20} /><div><h3>研究流程</h3><p>数据核查与划分 → 训练及验证选模 → 固定测试集评价 → 结果导出与可视化。</p></div></div>
        <TextLink to="/features">查看实现模块</TextLink>
      </Panel>
      <Panel title="数据与固定划分" subtitle="CAMUS · 500 名患者 · A2C / A4C" className={styles.article}>
        <div className={styles.split} aria-label="训练 400 人，验证 50 人，测试 50 人"><span /><span /><span /></div>
        <dl className={styles.splitStats}><div><dt>训练</dt><dd>400</dd></div><div><dt>验证</dt><dd>50</dd></div><div><dt>测试</dt><dd>50</dd></div></dl>
        <div className={styles.articleRow}><Database size={20} /><div><h3>患者级隔离</h3><p>同一患者的两个切面归入同一集合。训练归一化只使用训练数据，验证集用于权重及模型选择。</p></div></div>
      </Panel>
    </div>
    <div className={styles.twoCol}>
      <Panel title="测量方法与适用条件" className={styles.article}>
        <div className={styles.articleRow}><HeartPulse size={20} /><div><h3>空间和时间标定</h3><p>对有物理像素间距的轮廓估算单平面 Simpson 容积。A2C 与 A4C 独立采集，按各自时间序列处理。</p></div></div>
        <p>CAMUS 半周期缺少相邻两个 ED 峰，因此 HR、CO 记为缺测。容积参考由专家轮廓经同一几何法派生。</p>
        <Badge icon={ShieldCheck} tone="blue">研究基线 · 非临床验证</Badge>
      </Panel>
      <Panel title="数据与代码许可" className={styles.article}>
        <h3>CAMUS 数据</h3><p>CC BY-NC-SA 4.0。数据署名为 Leclerc 等，IEEE Transactions on Medical Imaging，2019。</p>
        <a href="https://doi.org/10.1109/TMI.2019.2900516" target="_blank" rel="noreferrer">CAMUS 原论文</a>
        <h3>EchoNet-Dynamic 代码</h3><p>官方代码采用 MIT 许可。影像数据使用权限按数据提供方的访问条款处理。</p>
        <a href="https://github.com/echonet/dynamic/blob/master/LICENSE" target="_blank" rel="noreferrer">EchoNet 官方代码许可</a>
      </Panel>
    </div>
  </div>
}
