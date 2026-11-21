"""从实际源码目录生成 README 结构；忽略环境缓存及运行产物的内容。"""
import argparse
import textwrap
from pathlib import Path

from ..config.paths import PROJECT_ROOT

START = '<!-- PROJECT_STRUCTURE:START -->'
END = '<!-- PROJECT_STRUCTURE:END -->'
RUNTIME_DIRECTORIES = {
    'data': '本地数据，Git 忽略；内部文件由数据集决定',
    'checkpoints': '本地模型权重，Git 忽略',
    'runs': '本地实验结果，Git 忽略',
}
GENERATED_DIRECTORIES = {
    'figures/fig_01_data_workflow': '已确认的Fig.1：队列与方法框架、PDF/600dpi位图、源数据、英文图注与检查',
    'figures/fig_02_segmentation_validation': '已确认的Fig.2：全患者分布及固定排名ED/ES病例、源数据、英文图注与检查',
    'figures/fig_03_function_agreement': '已确认的Fig.3：同法容积与CAMUS标签EF散点/BA、配对源数据、图注与检查',
    'figures/fig_04_half_sequence': '已确认的Fig.4：四固定病例真实ED–ES半序列轨迹、端点源数据、图注与检查',
    'figures/style_test': '已确认的全局样式测试页、真实源数据、英文图注及字体/排版/色觉检查',
    'figures/table_01_cohort': 'Table 1审阅稿：500患者队列与参考覆盖、可编辑表、PDF/600dpi、源数据及检查',
    'figures/table_02_function': 'Table 2审阅稿：五行主功能口径、患者配对、参考声明、图注及检查',
    'figures/workflow_parts': '当前项目流程图规划、独立零件及审阅图集；总图待讨论后组装',
    'reports/result_analysis': '实测结果图集、中文解读、源数据及图件检查；内容由绘图入口生成',
    'reports/result_integrity': '冻结结果全量复算、几何/EF偏倚/时序风险自检报告及逐项诊断数据；不改写原结果',
    'reports/training': '逐实验训练日志、每轮损失、运行环境与完成记录；内容由训练入口生成',
}
ENVIRONMENT_DIRECTORIES = {
    '.git', '.venv', '.idea', '.work', '.pytest_cache', '.pytest_work',
    'build', 'dist',
}
PRIVATE_PROJECT_FILES = {'AGENTS.md', 'task_extract.txt'}  # 本地协作约定与任务书提取件
DESCRIPTIONS = {
    '.github': 'GitHub 仓库自动化配置',
    '.github/workflows': '提交与拉取请求触发的自动检查流程',
    '.github/workflows/tests.yml': '安装核心测试依赖并运行 pytest；缺少可选依赖的测试会跳过',
    '.run': 'PyCharm 环境核查、三阶段与结果绘图配置；统一使用项目 .venv',
    '.run/CheckEnvironment.run.xml': '启动环境检查：核对项目 .venv、依赖版本和 CUDA',
    '.run/PlotResults.run.xml': '分析已保存实验并生成结果图，不重新训练或测试选模',
    '.run/Prepare.run.xml': '启动阶段 1：数据核查与固定患者划分',
    '.run/Test.run.xml': '启动阶段 3：测试集评价与结果导出',
    '.run/Train.run.xml': '启动阶段 2：模型训练与验证',
    'configs': '可注释的 YAML 实验配置及固定患者划分',
    'configs/data': '数据集路径、视图和处理约定',
    'configs/data/camus.yaml': 'CAMUS 数据目录、子集清单、患者数及预处理尺寸等参数',
    'configs/model': '模型结构与输入输出定义',
    'configs/model/deeplabv3_resnet50.yaml': 'DeepLabV3-ResNet50 名称、输入通道和前景输出通道',
    'configs/train': '训练超参数默认值',
    'configs/train/baseline.yaml': '训练轮数、batch、学习率、随机种子、设备及可选早停',
    'configs/camus_splits.json': '固定训练/验证/测试患者归属，防止同一患者跨集合',
    'configs/experiment.yaml': '实验总入口：合并组件配置，指定初始权重和训练/测试输出路径',
    'docs': '运行指南、全流程讲解、测量口径和数据来源材料',
    'docs/data_sources': '数据/权重来源、许可及完整性校验清单',
    'docs/data_sources/camus_download_manifest.json': 'CAMUS 原始文件路径、大小和 SHA256 校验清单',
    'docs/data_sources/CAMUS_LICENSE_TERMS.md': 'CAMUS 署名、CC BY-NC-SA 4.0 许可及使用条件',
    'docs/data_sources/echonet_weights.json': 'EchoNet 官方初始化权重的来源与校验信息',
    'docs/data_sources/official_patient_index.json': '官方患者、视图及原始文件的索引',
    'docs/data_sources/prepared_provenance.json': '处理后数据的代码/配置摘要、规模和审阅状态',
    'docs/code_walkthrough.md': '数据到结果表格的全链路、流程图、公式和逐文件讲解',
    'docs/measurement_protocol.md': '空间/时间标定、坐标恢复、指标与参考值的计算口径',
    'docs/patch_acquisition_workflow.md': '贴片 RF/IQ 到超声成像、模型接入与连续心功能分析的条件流程',
    'docs/pycharm_run.md': 'PyCharm 环境确认、三个入口运行和配置修改步骤',
    'docs/result_analysis.md': '结果图的证据设计、参考图适用范围、导出格式及复现方法',
    'figures': '论文图表规划、方法流程图、可编辑源稿和导出预览',
    'figures/_paper_common.py': '新投稿图共用的源数据溯源、物理坐标叠图、毫米排版及面板对齐检查',
    'figures/_paper_tables.py': '共享样式的三线表排版、逐单元格边界检查及可编辑Markdown导出',
    'figures/fig_01_data_workflow.py': '从冻结CAMUS队列与实际配置重建Fig.1数据和方法框架，不重新训练或推理',
    'figures/fig_02_segmentation_validation.py': '从全部82位测试患者和固定排名病例重建Fig.2，复核8帧轮廓指标',
    'figures/fig_03_function_agreement.py': '从冻结患者级配对重建Fig.3散点和Bland–Altman，分开参考口径并保留全部误差',
    'figures/fig_04_half_sequence.py': '重建Fig.4固定病例原始半序列容积及两个专家端点，不平滑或补造完整周期',
    'figures/style_test.py': '从冻结CAMUS结果重建样式测试页；使用共享样式，不重训或重选病例',
    'figures/table_01_cohort.py': '从1000侧车与固定划分重建队列统计，分别列患者和序列分母',
    'figures/table_02_function.py': '从冻结82患者配对重建五行功能统计，分开同法参考与CAMUS临床EF标签',
    'figures/planning': '结果资产盘点、同行逐图逐表拆解与图表规划的可复核材料',
    'figures/planning/audit_assets.py': '只读核查缓存、患者划分和冻结源文件，不重训或重选模型',
    'figures/planning/audit_results.py': '重算全部测试标注帧与功能算术，审计代理几何覆盖和时序风险，不改冻结结果',
    'figures/planning/asset_inventory.json': '缓存规模、空间时间范围、冻结来源校验与现有实验清单',
    'figures/planning/result_assets.md': '输出资产、分辨率、实验和已算/待算/不可算指标的中文清单',
    'figures/planning/literature_catalog.json': '六篇已读论文逐图表结构、原始图注和来源校验记录',
    'figures/planning/summarize_literature.py': '从人工核查目录生成拆解表并统计图表数量与论证作用',
    'figures/planning/literature_statistics.json': '图表数量中位数、范围和十二类论证作用的统计结果',
    'figures/planning/literature_breakdown.md': '两篇模板与四篇近期论文的逐图逐表拆解及共同做法',
    'figures/planning/visualization_coverage.md': '结果分析可视化覆盖审计、正文/补充/质控分层及不可制作项目',
    'figure_plan.md': '正文和补充图表制作清单、证据边界、待补计算与阶段确认进度',
    'style': '所有新投稿图共用的字体、色系、色带、尺寸与导出设置',
    'style/paper.mplstyle': '用户选定的Nature/Arial全局样式：普通文字7pt、600dpi位图',
    'style/palette.py': '固定实验/参考配色、cividis/vik色带、字体与物理尺寸及统一导出',
    'style/requirements.txt': '样式绘图、科学色带和PDF/色觉检查所需依赖',
    'style/README.md': '已确认的全局样式映射、期刊尺寸、复现方法及导出约定',
    'figures/camus_method_flow.svg': 'CAMUS 左室分割与心功能参数估算可编辑流程图',
    'figures/camus_method_flow.pdf': '用于论文排版的矢量版方法流程图',
    'figures/camus_method_flow.png': '由 SVG 源稿生成的流程图预览',
    'figures/method_flow_caption.md': '流程图图注、核心主张和实现假设',
    'figures/render_method_flow.py': '从 SVG 导出保留文字的矢量 PDF 和 300 dpi 预览',
    'figures/method_flow_export_check.json': '导出尺寸、文字边界和重叠检查记录',
    'reports': '历史基线结果、训练日志与审计；不代表当前代码已重新训练',
    'reports/full_baseline': '历史完整基线的汇总指标、患者特征和训练记录',
    'reports/full_baseline/patient_features.csv': '患者级预测/参考心功能特征表',
    'reports/full_baseline/RESULTS.md': '历史基线结果、数据规模、参考口径及局限说明',
    'reports/full_baseline/summary.json': '分割与心功能评价的结构化汇总',
    'reports/full_baseline/training_history.csv': '历史每轮训练/验证损失记录',
    'reports/full_baseline/training_run.json': '历史训练参数、患者划分、归一化和运行溯源',
    'reports/input_equivalence.json': '历史本地输入与处理后发布数据包的一致性审计',
    'reports/release_artifacts.json': '历史结果发布归档的大小、摘要及校验信息',
    'reports/source_integrity.json': '历史评价源码与被记录提交的对应关系审计',
    'reports/visualization_literature.md': '十二篇相关文献的结果图设计依据、参考流程图核对和论文建议',
    'reports/visualization_sources.json': '本次图件调研的核验题录、摘要、来源及查阅范围',
    'scripts': '可直接在 PyCharm 运行的薄入口及辅助工具',
    'scripts/check_environment.py': '核对 PyCharm 是否使用项目 .venv，并报告依赖版本与 CUDA 状态',
    'scripts/download_weights.py': '可选下载 EchoNet 初始化权重并核查摘要，不下载数据集',
    'scripts/evaluate.py': '阶段 3：检查测试清单/权重，调用评估引擎生成结果',
    'scripts/fix_windows_torch_runtime.py': '专项修复 Windows/Anaconda C++ 运行库冲突，非日常步骤',
    'scripts/prepare_data.py': '阶段 1：核查已有处理后数据，生成固定患者级三份子集清单',
    'scripts/plot_results.py': '从匹配的冻结实验导出患者级图集及可追溯源数据',
    'scripts/train.py': '阶段 2：读取训练/验证清单，启动训练并保存配置和完成记录',
    'src': '项目算法与工程实现，按职责拆分的 Python 源码包',
    'src/config': 'YAML 配置加载、默认值合并和路径解析',
    'src/config/loader.py': '安全读取 YAML、递归合并组件/覆盖值并记录配置文件摘要',
    'src/config/paths.py': '定位项目根目录，统一解析配置中的相对路径',
    'src/data': '通用数据适配、清单、固定划分、影像读取与坐标/元数据处理',
    'src/data/camus': 'CAMUS 专用适配及独立原始数据工具；日常流程读取已有缓存',
    'src/data/camus/dataset.py': 'CAMUS 适配器与 Dataset，仅以专家标注 ED/ES 帧监督训练',
    'src/data/camus/download.py': '可选独立归档下载，要求 HTTPS 来源与可信 SHA256',
    'src/data/camus/prepare.py': '可选原始数组处理：左室标签、声窗、裁剪/缩放及原始标注审计',
    'src/data/base.py': '数据适配器接口与带标注帧 Dataset，供训练和评价统一读取',
    'src/data/manifests.py': '读取子集病例清单，解析数据根目录并校验源 manifest 摘要',
    'src/data/medical_io.py': '读取医学影像/视频及轮廓标注，提取可用空间与时间信息',
    'src/data/metadata.py': '审计帧数、像素间距、帧率和时间戳，明确缺失及推导来源',
    'src/data/prepare.py': '核查处理后数据、原始标签/坐标审计并生成三份子集清单',
    'src/data/splits.py': '患者级固定划分及集合隔离检查',
    'src/data/transforms.py': '裁剪/缩放正反坐标映射、掩膜恢复与训练归一化',
    'src/engine': '训练、验证、最终评价与进度/选模回调',
    'src/engine/callbacks.py': '时间戳日志、批次进度与速度、最佳权重保存及可选早停',
    'src/engine/evaluator.py': '测试推理、恢复原始坐标、提取特征并汇总指标和报告',
    'src/engine/trainer.py': '训练集统计归一化、AdamW/BCE 训练和验证损失选模',
    'src/geometry': '左室掩膜几何测量、单/双平面容积与心功能计算',
    'src/geometry/functional.py': 'EDV/ESV → SV/EF；仅在心率可靠时计算 CO',
    'src/geometry/mask_features.py': '掩膜 → 面积、长轴、轮廓派生关键点与截面直径',
    'src/geometry/volume.py': '单平面面积-长轴法及双平面圆盘法容积估算',
    'src/metrics': '分割、关键点、心功能与时序定位误差',
    'src/metrics/cardiac.py': '按患者汇总心功能 MAE、偏倚及不确定性',
    'src/metrics/segmentation.py': 'Dice、ASSD、HD95 及关键点距离误差',
    'src/metrics/temporal.py': 'ED/ES 相位帧差；时间戳可靠时换算秒误差',
    'src/models': '模型工厂、DeepLabV3 网络及损失函数',
    'src/models/build.py': '按配置创建网络、兼容 EchoNet 检查点并分批推理',
    'src/models/deeplabv3.py': '构建 EchoNet 风格的单前景 DeepLabV3-ResNet50 分割网络',
    'src/models/losses.py': '计算均值二元交叉熵 BCE 分割损失',
    'src/temporal': '可选时序分析；不拼接/反射半周期伪造完整心搏',
    'src/temporal/beat_detection.py': '在可靠时间与完整序列上识别心动周期并计算周期特征',
    'src/temporal/quality_gate.py': '根据几何/时间连续性标记质量异常帧',
    'src/temporal/smoothing.py': '对容积等时序曲线进行平滑',
    'src/utils': '读写、溯源、设备、随机种子及 README 结构维护工具',
    'src/utils/device.py': '选择 CUDA/CPU 并设置 CPU 线程数',
    'src/utils/hash.py': 'SHA256 与代码/运行来源记录',
    'src/utils/io.py': 'JSON/NPZ 读写及 CSV 结果导出',
    'src/utils/project_structure.py': '按实际文件生成带功能注释的目录树并检查 README 一致性',
    'src/utils/run.py': '保护已有输出目录，保存阶段配置与数据检查快照',
    'src/utils/runtime.py': '记录 Python/依赖/CUDA 版本并校验项目虚拟环境',
    'src/utils/seed.py': '设置 Python、NumPy、PyTorch/CUDA 随机种子',
    'src/visualization': '预测叠图、曲线及离线 HTML 报告',
    'src/visualization/analysis.py': '核验实验来源，绘制训练/分割/一致性/覆盖率及失败病例图',
    'src/visualization/overlay.py': '将预测/参考轮廓叠加到超声图像',
    'src/visualization/plots.py': '绘制容积等时序曲线',
    'src/visualization/report.py': '汇总指标、图像和曲线生成离线 HTML 报告',
    'tests': '自动工程回归检查，不替代真实患者实验或临床验证',
    'tests/test_camus.py': '检查左室标签身份、原始标注/坐标保留及声窗保护回退',
    'tests/test_config.py': '检查 YAML 合并、路径、模型工厂与三阶段入口衔接',
    'tests/test_experiment.py': '检查处理后数据审计、子集清单与输出目录保护',
    'tests/test_geometry.py': '检查几何、容积、心功能及周期计算',
    'tests/test_io.py': '检查 EchoNet 轮廓 CSV 转掩膜及对应帧身份',
    'tests/test_model.py': '检查 DeepLabV3 输出及检查点加载兼容性',
    'tests/test_pipeline.py': '检查模拟预测到结果导出的流程和缺失参考处理',
    'tests/test_preprocess.py': '检查图像排除区、插值、时间缺失及患者隔离',
    'tests/test_project_structure.py': '检查 README 目录树与实际文件一致、文档本地链接有效',
    'tests/test_result_analysis.py': '检查实验混用、患者泄漏、参考来源、缺失值及配对统计保护',
    'tests/test_runtime.py': '检查运行环境元数据和项目虚拟环境守卫',
    'tests/test_training_progress.py': '检查训练进度/吞吐量记录、验证选模及早停',
    'vendor': '保留固定版本上游代码、来源和许可',
    'vendor/echonet': 'EchoNet 上游参考实现，独立于本项目三阶段入口',
    'vendor/echonet/echonet': '上游 EchoNet Python 包',
    'vendor/echonet/echonet/datasets': '上游 EchoNet-Dynamic 数据集读取模块',
    'vendor/echonet/echonet/datasets/echo.py': '上游视频、患者划分、EF 和轮廓标签读取实现',
    'vendor/echonet/echonet/utils': '上游图像/视频工具及训练任务',
    'vendor/echonet/echonet/utils/__init__.py': '上游视频读写、统计与通用工具导出',
    'vendor/echonet/echonet/utils/segmentation.py': '上游分割训练/评价实现，供基线来源核对',
    'vendor/echonet/echonet/utils/video.py': '上游视频 EF 回归任务，未接入当前 CAMUS 流程',
    'vendor/echonet/echonet/__init__.py': '上游包初始化，导出数据与工具模块',
    'vendor/echonet/echonet/__main__.py': '上游命令行任务入口，非本项目日常入口',
    'vendor/echonet/echonet/__version__.py': '上游包版本声明',
    'vendor/echonet/echonet/config.py': '上游数据路径等配置读取',
    'vendor/echonet/.gitignore': '上游仓库的文件忽略约定',
    'vendor/echonet/example.cfg': '上游配置示例，非当前 YAML 实验配置',
    'vendor/echonet/LICENSE': 'EchoNet 上游 MIT 许可证',
    'vendor/echonet/README.md': '上游项目说明与使用方法',
    'vendor/echonet/requirements.txt': '上游依赖清单，当前项目依赖以根目录文件为准',
    'vendor/echonet/setup.py': '上游打包脚本；本项目使用根目录 pyproject.toml',
    'vendor/echonet_source.json': '上游仓库、固定提交、归档 SHA256 与许可来源',
    '.gitattributes': '文本换行和医学影像/模型等 Git LFS 类型规则',
    '.gitignore': '排除本机环境、数据、权重、运行产物和私有协作文件',
    'pyproject.toml': '项目元数据、可选依赖、安装入口及 pytest 配置',
    'README.md': '项目概览、带功能注释的文件树和运行方法',
    'requirements.txt': '完整运行依赖清单；CUDA 版 PyTorch 需匹配驱动安装',
}


def _description(path, root):
    """按相对路径注释每项；新增文件必须补充说明，避免静默遗漏。"""
    relative = path.relative_to(root).as_posix()
    if relative in RUNTIME_DIRECTORIES:
        return RUNTIME_DIRECTORIES[relative]
    if relative in GENERATED_DIRECTORIES:
        return GENERATED_DIRECTORIES[relative]
    if relative in DESCRIPTIONS:
        return DESCRIPTIONS[relative]
    if path.name == '__init__.py':
        return 'Python 包初始化与模块说明，无需单独运行'
    raise ValueError(f'请在 project_structure.py 中补充功能说明：{relative}')


def _visible(path, root):
    """仅排除明确的本机环境和可再生缓存，其余源码/文档必须列出。"""
    if path.name == '__pycache__' or path.suffix in ('.pyc', '.pyo') or path.name.startswith('~$'):
        return False
    if path.parent == root:
        return (
            path.name not in ENVIRONMENT_DIRECTORIES
            and path.name not in PRIVATE_PROJECT_FILES
            and not path.name.endswith('.egg-info')
        )
    return True


def render_tree(root=PROJECT_ROOT):
    """完整列出项目文件，并把功能说明放到对应路径的下一行。"""
    root = Path(root).resolve()
    lines = ['Echo/', '# 左心室分割与心功能分析项目根目录']

    def visit(directory, prefix=''):
        entries = {p.name: p for p in directory.iterdir() if _visible(p, root)}
        if directory == root:
            # Git 新检出时运行目录可能不存在，说明中仍展示其约定位置。
            entries.update({name: root / name for name in RUNTIME_DIRECTORIES})
        ordered = sorted(entries.values(), key=lambda p: (
            not (p.is_dir() or (directory == root and p.name in RUNTIME_DIRECTORIES)),
            p.name.casefold(),
        ))
        for index, path in enumerate(ordered):
            last = index == len(ordered) - 1
            runtime = path.relative_to(root).as_posix() in (RUNTIME_DIRECTORIES | GENERATED_DIRECTORIES)
            is_directory = runtime or path.is_dir()
            label = path.name + ('/' if is_directory else '')
            lines.append(prefix + ('└── ' if last else '├── ') + label)
            description_prefix = prefix + ('    ' if last else '│   ')
            description_lines = textwrap.wrap(
                _description(path, root),
                width=max(24, 54 - len(description_prefix)),
                break_long_words=False,
                break_on_hyphens=False,
            ) or ['']
            lines.extend(description_prefix + '# ' + line for line in description_lines)
            if is_directory and not runtime:
                visit(path, prefix + ('    ' if last else '│   '))

    visit(root)
    return '\n'.join(lines)


def structure_block(root=PROJECT_ROOT):
    return START + '\n```text\n' + render_tree(root) + '\n```\n' + END


def update_readme(root=PROJECT_ROOT, check=False):
    """只更新受标记的结构块；check 模式发现差异时报错，不改文件。"""
    root = Path(root).resolve()
    path = root / 'README.md'
    content = path.read_text(encoding='utf-8')
    if content.count(START) != 1 or content.count(END) != 1:
        raise ValueError('README 必须包含唯一的目录结构起止标记。')
    start = content.index(START)
    end = content.index(END, start) + len(END)
    expected = structure_block(root)
    matches = content[start:end] == expected
    if check and not matches:
        raise ValueError('README 目录与实际文件不一致，请运行 python -m src.utils.project_structure --write')
    if not check and not matches:
        path.write_text(content[:start] + expected + content[end:], encoding='utf-8', newline='\n')
    return matches


def main(argv=None):
    parser = argparse.ArgumentParser(description='生成或核查 README 的实际项目目录')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--write', action='store_true', help='根据实际文件更新 README 目录')
    mode.add_argument('--check', action='store_true', help='只检查一致性')
    options = parser.parse_args(argv)
    update_readme(check=options.check)
    print('README directory matches project files.' if options.check else 'README directory updated.')


if __name__ == '__main__':
    main()
