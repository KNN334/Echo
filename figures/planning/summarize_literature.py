"""Render the curated paper inventory and recompute display/role counts."""
import json
from pathlib import Path
from statistics import median


DIRECTORY = Path(__file__).resolve().parent


def main():
    catalog = json.loads((DIRECTORY / 'literature_catalog.json').read_text(encoding='utf-8'))
    papers = catalog['papers']
    items = catalog['display_items']
    main_items = [item for item in items if item['section'] == '正文']
    main_figures = [item for item in main_items if item['number'].startswith('Fig.')]
    counts = []
    for paper in papers:
        si = paper['supplementary_figures']
        counts.append({'paper': paper['label'], 'main_figures': paper['main_figures'],
                       'main_tables': paper['main_tables'], 'extended_figures': paper['extended_figures'],
                       'extended_tables': paper['extended_tables'], 'supplementary_figures': si,
                       'supplementary_tables': paper['supplementary_tables'],
                       'nonmain_figures_total': None if si is None else si + paper['extended_figures']})
    role_counts = []
    for role in catalog['roles']:
        matching = [item for item in main_items if role in item['roles']]
        all_matching = [item for item in items if role in item['roles']]
        role_counts.append({'role': role, 'main_display_items': len(matching),
                            'main_figures': sum(role in item['roles'] for item in main_figures),
                            'papers_with_main_item': len({item['paper'] for item in matching}),
                            'all_curated_display_items': len(all_matching),
                            'papers_with_any_item': len({item['paper'] for item in all_matching})})
    stats = {'paper_count': len(papers), 'main_display_item_count': len(main_items),
             'main_figure_count': len(main_figures), 'total_curated_items': len(items),
             'counts': counts, 'main_role_counts': role_counts}
    for key in ['main_figures', 'main_tables', 'nonmain_figures_total']:
        values = [count[key] for count in counts if count[key] is not None]
        stats[key + '_summary'] = {'n_papers': len(values), 'median': median(values),
                                  'min': min(values), 'max': max(values)}
    (DIRECTORY / 'literature_statistics.json').write_text(json.dumps(stats, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = ['# 同行论文逐图逐表拆解', '',
             '阅读与核查日期：2026-11-20。两篇模板已由用户确认；另选4篇近三年原始研究。所有正文图均核对原图与图注；扩展图核对原图，SI核对可得PDF/DOCX及图注。视频未逐帧分析。共162个图表条目。', '',
             '这是为本研究选择图表证据的叙述性样本，不是领域普查。表格没有把不同论文的结果数值直接当作可比基线。图像与统计单元按字母分组计数，嵌套小图另说明；非规则布局不强填成规则网格。', '',
             '## 来源与纳入范围', '']
    for paper in papers:
        lines += [f"- **{paper['label']}**：{paper['title']}. *{paper['journal']}*. [{paper['doi']}](https://doi.org/{paper['doi']})；[核查全文]({paper['fulltext']})。{paper.get('date_note', '')}{paper.get('relevance', '')}{paper.get('supplement_note', '')}"]
        if 'supplement' in paper:
            lines += [f"  补充材料：[原始附件/官方归档]({paper['supplement']})。"]
    lines += ['', '## 数量统计与口径', '',
              '| 论文 | 正文图 | 正文表 | 扩展图 | 扩展表 | SI图 | SI表 | 非正文图合计 |',
              '|---|---:|---:|---:|---:|---:|---:|---:|']
    for count in counts:
        values = [count[k] for k in ['paper', 'main_figures', 'main_tables', 'extended_figures', 'extended_tables', 'supplementary_figures', 'supplementary_tables', 'nonmain_figures_total']]
        lines.append('| ' + ' | '.join('NA' if value is None else str(value) for value in values) + ' |')
    for key, label in [('main_figures', '正文图'), ('main_tables', '正文表'), ('nonmain_figures_total', '非正文图（Extended Data+SI）')]:
        data = stats[key + '_summary']
        lines += ['', f"{label}：中位数 **{data['median']}**，范围 **{data['min']}–{data['max']}**，统计分母 {data['n_papers']} 篇。"]
    lines += ['', 'EchoFM的独立SI未查明，NA不按0处理；因此非正文图统计只有5篇。正文图/表均按6篇计算。Hu/Ouyang是指定的历史模板，明确不算作“近三年论文”。EchoPrime在线2025、卷期2026，不重复纳入。', '',
              '## 正文论证作用频率', '',
              '使用用户指定的12类，可多标签。每个编号图/表每类最多计一次，不能将子图数当图数。正文有26图+16表=42个条目，正文/扩展/SI共162个已核查条目；同时给出论文覆盖率以免被TMI较多表格支配。全部条目的频率限于已获得材料，不含EchoFM未知SI。', '',
              '| 论证作用 | 正文图 / 26 | 正文图表 / 42 | 正文出现论文 / 6 | 全部条目 / 162 | 任一位置出现论文 / 6 |', '|---|---:|---:|---:|---:|---:|']
    for count in role_counts:
        lines += [f"| {count['role']} | {count['main_figures']} | {count['main_display_items']} | {count['papers_with_main_item']} | {count['all_curated_display_items']} | {count['papers_with_any_item']} |"]
    lines += ['', '计算效率按网络计算/显存/参数量归类：Chao Fig.3是人工辅助标注效率，SAFU SI Table 6是制造成本，均不计作计算效率；它们的其他作用仍保留。正文计算效率为0不代表整篇未报告，Ouyang扩展数据提供计算代价。']
    lines += ['', '## 能迁移到本项目的共同做法', '',
              '- 正文流程/框架见5/6篇；把“输入是什么、方法做什么、输出如何验证”放在读者最先看到的位置。Chao以分割样例和性能表为主，没有硬塞一张流程图。',
              '- 分割定性样例见4/6篇（Hu在扩展数据；Ouyang、Chao、EchoFM在正文）。Chao明确展示低分位样例，适合本项目固定排名并保留最差病例。',
              '- 内外部或跨数据域比较见Ouyang、Chao、EchoFM、EchoPrime四篇。SAFU不同部位/运动工况是器件能力边界，不能直接等同跨医院AI泛化。',
              '- Bland–Altman在本批明确见Hu Fig.5c及EchoPrime SI Fig.1（2/6）；独立EF回归散点正文见Ouyang Fig.2a（1/6）；损失曲线见Ouyang ED Fig.3（1/6）。它们并非“几乎每篇都有”，按证据需要选择。',
              '- 时间过程见Hu/Ouyang/SAFU的真实测量；EchoFM的时间矩阵表示模型表征，不是心功能真值曲线。当前CAMUS只能画真实ED→ES半序列，不能照搬恢复期HR/CO。',
              '- 表格承载多方法/多任务数值，图承载主要证据与异常。正文表中位1.5，建议本项目2表；正文图中位4，建议本项目4图。按样本统计配额不能替代目标期刊最终作者指南。',
              '- 本项目的可验证长处是溯源、原坐标空间评价、参考层级分开、全病例与失败覆盖。没有新架构/多中心/贴片数据时，不能通过视觉设计制造这些优势。', '',
              '## 逐篇逐图逐表', '']
    for paper in papers:
        lines += [f"### {paper['label']}", '']
        for section in ['正文', '扩展数据', '补充材料']:
            selected = [item for item in items if item['paper'] == paper['id'] and item['section'] == section]
            if not selected:
                continue
            lines += [f'**{section}**', '', '| 论文 | 图号 | 图表类型 | 展示内容 | 子图数量与排版 | 所用数据维度 | 在论证中的作用 | 配色与视觉特点 |', '|---|---|---|---|---|---|---|---|']
            for item in selected:
                values = [paper['label'], item['number'], item['type'], item['content'], item['layout'], item['dimensions'], '；'.join(item['roles']), item['visual']]
                lines += ['| ' + ' | '.join(value.replace('|', '/') for value in values) + ' |']
            lines += ['']
    lines += ['## 检索和访问记录', '',
              'Europe PMC：近三年宽查询3954条，指定期刊+echo/可穿戴心脏超声查询242条（均为本次接口hitCount，不是逐条人工筛查人数）。选择4篇可读全文的原始研究；期刊覆盖Nature、npj Digital Medicine、IEEE TMI、Science Advances，未为凑期刊覆盖而虚构Biosensors/JBHI/MedIA文献。', '',
              'Europe PMC的Ouyang/EchoFM fullTextXML端点返回HTTP 500，改读Nature全文/PMC开放作者稿。Science补充材料直链先返回HTML/访问验证，最终通过Europe PMC合法supplementaryFiles包取得真实PDF，并核对文件头、正文和26图8表目录。所有纳入正文均非“仅有摘要”；EchoFM独立SI缺口如上保留。', '',
              '原始摘录、逐图人工归类、全文/附件SHA256及网址见 [literature_catalog.json](literature_catalog.json)；数量由 [summarize_literature.py](summarize_literature.py) 计算，结果见 [literature_statistics.json](literature_statistics.json)。公开原图只用于核查，不作为本项目投稿图素材；图号借鉴不等于复制像素、结果或文献的样本数。', '']
    (DIRECTORY / 'literature_breakdown.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({key: stats[key] for key in ['total_curated_items', 'main_figures_summary', 'main_tables_summary', 'nonmain_figures_total_summary']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
