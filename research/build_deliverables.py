import json, pathlib, datetime, math, re, zipfile, shutil, xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.pagebreak import Break
from PIL import Image, ImageDraw, ImageFont

ROOT=pathlib.Path(__file__).resolve().parent.parent
OUT=ROOT/'outputs/开题准备_20261107'
QA=ROOT/'research/qa'
OUT.mkdir(parents=True,exist_ok=True); QA.mkdir(parents=True,exist_ok=True)
P=json.loads((ROOT/'research/papers.json').read_text(encoding='utf-8'))
D=json.loads((ROOT/'research/drafts.json').read_text(encoding='utf-8'))
M=json.loads((ROOT/'research/metrics.json').read_text(encoding='utf-8'))
NAVY='173B55'; TEAL='137D86'; LIGHT='EAF3F5'; INK='22313F'; GREY='607080'

wb=Workbook(); wb.remove(wb.active)
def sheet(name,headers,rows,widths,heights=66,freeze='A2'):
    s=wb.create_sheet(name); s.append(headers)
    for row in rows: s.append(row)
    for i,w in enumerate(widths,1): s.column_dimensions[get_column_letter(i)].width=w
    s.freeze_panes=freeze; s.sheet_view.showGridLines=False
    s.sheet_properties.pageSetUpPr.fitToPage=True
    s.page_setup.orientation='landscape'; s.page_setup.paperSize=s.PAPERSIZE_A3
    s.page_setup.fitToWidth=1; s.page_setup.fitToHeight=0
    s.print_title_rows='1:1'; s.print_options.horizontalCentered=False
    s.oddFooter.center.text='第 &P 页 / 共 &N 页'; s.oddFooter.right.text='开题准备 · 2026-11-07'
    for c in s[1]:
        c.font=Font(name='Microsoft YaHei',size=11,bold=True,color='FFFFFF')
        c.fill=PatternFill('solid',fgColor=NAVY)
        c.alignment=Alignment(horizontal='left',vertical='center',wrap_text=True)
    s.row_dimensions[1].height=36
    for row in s.iter_rows(min_row=2):
        s.row_dimensions[row[0].row].height=heights
        for c in row:
            c.font=Font(name='Microsoft YaHei',size=10,color=INK)
            c.alignment=Alignment(horizontal='left',vertical='top',wrap_text=True)
            if c.row%2==0:c.fill=PatternFill('solid',fgColor='F1F6F8')
            c.border=Border(bottom=Side(style='hair',color='D8E3E9'))
    tab=Table(displayName='T'+str(len(wb.worksheets)),ref=s.dimensions)
    tab.tableStyleInfo=TableStyleInfo(name='TableStyleMedium2',showRowStripes=True)
    s.add_table(tab)
    return s

nav=sheet('阅读导航',['编号','主题','优先级','中文导读','期刊','卷期年','本课题用途','阅读依据'],
 [[p['id'],p['group'],p['priority'],p['zh'],p['journal'],p['year'],p['use'],p['evidence']] for p in P],
 [7,21,9,47,34,10,70,58],84,'D2')
for row in range(2,22):
    c=nav.cell(row,1);c.hyperlink=f"#'文献矩阵'!A{row}";c.font=Font(name='Microsoft YaHei',color=TEAL,underline='single')

headers=['编号','研究模块','贴合度','优先级(1先读)','英文题名','中文导读','作者(前三位)','期刊来源','影响因子(数值)','IF统计年/页面口径','在线/首发日期','日期精度说明','卷期出版时间','主要工作','主要结论/结果','创新点(研究贡献)','不足/适用边界','不足判断依据','本课题启示','DOI','原文链接','题录/摘要来源','内容核验状态','数据/代码入口与条件']
rows=[]
for p in P:
    rows.append([p['id'],p['group'],p['relevance'],p['priority'],p['title'],p['zh'],p['authors'],p['journal'],p['metric'][0],p['metric'][1],datetime.datetime.fromisoformat(p['online']),p['date_basis'],p['issue_date'],p['work'],p['result'],p['innovation'],p['limits'],p['limit_basis'],p['use'],p['doi'],p['url'],p['record_url'],p['evidence'],p['data']])
mat=sheet('文献矩阵',headers,rows,[7,21,33,12,65,44,30,37,13,45,15,42,18,65,65,58,70,55,65,40,53,47,60,72],168,'E2')
for row in range(2,22):
    mat.cell(row,9).number_format='0.0';mat.cell(row,11).number_format='yyyy-mm-dd'
    for col in [21,22]:
        mat.cell(row,col).hyperlink=mat.cell(row,col).value
        mat.cell(row,col).font=Font(name='Microsoft YaHei',size=10,color=TEAL,underline='single')

met=sheet('期刊指标',['期刊','IF数值','统计年/页面口径','核验层级与限制','来源URL','检索日期'],
 [[name,*v,datetime.datetime(2026,11,7)] for name,v in M.items()], [47,13,62,77,83,16],72)
for row in range(2,14):met.cell(row,2).number_format='0.0';met.cell(row,6).number_format='yyyy-mm-dd'

boundary=[
 ['研究定位','已明确','以任务书的左室结构提取→SV/EF/CO→分析可视化为主线','当前设备和数据尚未确定；不预设已有贴片样本','计划书1、3节'],
 ['容积模型','按切面选择','有效时间对应A4C/A2C优先双平面圆盘法；单切面声明近似','不把PLAX和心尖视图直接套同一公式，不把面积变化率当EF','[1,14,18,19]'],
 ['SV (mL)','SV=EDV−ESV','需要ED/ES容积及空间标定','显著瓣膜反流时，容积差不等于前向有效血流','[18]；方法学说明'],
 ['EF (%)','EF=(EDV−ESV)/EDV×100','EF误差用绝对百分点报告','直接回归EF不能据此推出绝对SV/CO；单切面有几何偏差','[11,18]'],
 ['CO (L/min)','CO_i=SV_i×HR_i/1000','HR_i=60/T_i；说明逐搏等效量','需要空间标定和时间标定；缺失窗口不能直接做完整时间积分','[1]；计划书5节'],
 ['缺少空间标定','不输出绝对mL/L/min','可研究像素面积曲线和相对变化','无量纲EF仍受几何与切面假设限制','计划书5、9节'],
 ['质量失效','识别并标记无效','图像严重遮挡、截断、切面漂移或周期不可信时拒绝定量','插值/补全需单独标记，不计原始有效观测','[1,8]；研究设计'],
 ['连续监测评价','误差与覆盖率联合报告','结构、功能、覆盖率、缺失率、延迟分层评价','仅筛选成功片段可能夸大精度；需同覆盖率比较','计划书6、7节'],
 ['样本独立性','患者级切分与重采样','同一人的帧、心搏、片段不能跨训练/测试泄漏','心搏数不等于独立受试者数','[11,12]；统计设计'],
 ['证据边界','本轮为目标性文献筛选','题录全核验；部分重点全文，其余摘要/题录','不称为系统综述或20篇全部全文精读','检索记录与矩阵W列'],
 ['影响因子口径','当前可见期刊指标','官网明示统计年和二级来源分开；不与发表年混淆','二级来源与未标统计年条目待学校JCR核实','期刊指标'],
 ['阅读顺序','1→11→14→18→8→16→17','先了解贴片闭环、公开基线、几何方法，再读新算法','指南具体条款需在实现前定位全文','阅读导航']
]
sheet('参数与边界',['事项','规则/公式','条件与说明','限制/处理','证据/对应章节'],boundary,[25,52,92,92,43],78)

schedule=[
 ['1–2周','文献/资源','精读[1,11,14,18]与[8,16,17]；核实数据许可、算力和参考','导师、数据平台','范围清单、数据字典、开题稿','第2周确认真实贴片路径；无路径先走公开数据','必做'],
 ['3–4周','基线','患者级划分；读取标定/时间；分割基线与几何核验','数据准入','可运行基线、独立验证指标、问题清单','基线未跑通前不增加复杂网络','必做'],
 ['5–6周','量化闭环','容积曲线、ED/ES、SV/EF/CO；明确不可计算条件','切面、标定、帧率','逐搏参数模块、人工审查子集','第6周决定是否真实贴片验证；无数据确认替代范围','必做'],
 ['7–8周','方法改进','最小必要时序模块和质量门控；验证集确定阈值','稳定基线','改进模块、失效样例、固定实验方案','相同覆盖率比较；不以强平滑掩盖真实变化','必做'],
 ['9–10周','消融统计','逐帧/时序/门控/联合对照；患者聚类置信区间','测试前固定方案','误差–覆盖率曲线、边界/功能误差及振幅检查','不以测试集调参；不把心搏当独立样本','必做'],
 ['11–12周','跨域与鲁棒性','公开跨域、受控扰动；如有真实贴片，独立受试者验证','可用外部数据','分场景验证与缺失/漂移报告','合成退化与真实采集分开；不做无依据临床结论','基础必做；真实贴片条件性'],
 ['13–14周','系统/写作','分析界面、导出、运行配置、论文图表','方法与实验稳定','系统原型、复现说明、论文结果章节','保留原始/推断/无效标志','必做'],
 ['15–16周','提交/答辩','全文、公式、引用复核；演示与归档','导师审阅与教学日历','毕业论文、演示、代码与数据说明','预留修改；不新增主要模型','必做'],
 ['启动前','待导师确认','设备/数据来源，开题/答辩日期与模板，算力和人工参考支持','导师反馈','学校时间表、实际资源边界','周次为相对安排，未假定答辩日','待确认'],
 ['阶段目标','工程参考','Dice约0.90、EF MAE力争≤6个百分点；性能目标≥20 FPS','以具体数据和硬件为准','第4周据基线固定正式比较标准','非临床阈值、非已达成结果、非保证承诺','拟定'],
 ['真实样本','先导设计备选','资源允许可探索10–20名受试者、每人2–3个条件/重复片段','合规采集/共享与参考','实际方案及受试者层面精度估计','非功效分析；小样本只做探索','条件性']
]
sheet('执行计划',['阶段','工作包','工作内容','依赖/前提','交付物','验收/决策规则','状态'],schedule,[17,20,94,42,61,83,29],88)

queries=[
 ['项目依据','本地任务书','2-毕业设计（论文）任务书.docx','已读取研究基本内容；重点为左室图像与SV/EF/CO自动分析','任务书原件'],
 ['检索截止','2026-11-07','检索日期使用Asia/Shanghai；纳入截止前已发表正式期刊文献','非完整系统综述；不提供未经去重审核的纳排流程计数','当前会话'],
 ['检索平台','Europe PMC','https://www.ebi.ac.uk/europepmc/webservices/rest/search','用于题名、作者、DOI、在线/卷期日期和摘要核验；按DOI补充追溯','每篇矩阵V列可追溯'],
 ['器件初检','关键词组合','(wearable OR stretchable OR bioadhesive) AND ultrasound；2018-01-01至2026-11-07','筛选心脏/心血管连续监测，排除仅治疗/药物递送等无关工作','缓存wearable.json'],
 ['心脏初检','关键词组合','ultrasound AND (cardiac OR echocardiography) AND wearable；2023-01-01至截止日','优先真实心脏成像与功能参数系统；血压研究明确标B支撑','缓存cardiac.json'],
 ['算法初检','关键词组合','echocardiography AND (video-based OR segmentation OR CAMUS OR EchoNet)；2018年至截止日','定向追溯高质量公开基线、外部验证与近期时序/跨域方法','缓存echoAI.json及DOI补查'],
 ['规范追溯','指南','成人心腔定量2015；成人完整经胸检查指南在线2018/卷期2019','用于测量口径，非贴片临床性能证据','[18,19]'],
 ['全文核验','重点正文','[1] Nature；[3] Nature Biotechnology；[8] Europe PMC全文；[16] npj Digital Medicine','重点检查方法范围与限制；补充材料未逐项精读；其余按矩阵标记','公开原文链接见矩阵U列'],
 ['IF核验','官网与二级来源','官网明示2025 JIF：Nature/NBT/NBE/npj Digital Medicine/Microsystems；TMI未明示统计年','其余公开二级来源数值与年份待JCR复核；不是发表当年IF','期刊指标表'],
 ['不足口径','区分证据与分析','有作者明确限制时注明；仅摘要条目以课题适用性分析为主','不把未见完整临床验证等同于作者没有开展；不虚构样本量或结论','矩阵Q/R/W列'],
 ['数据状态','尚未取得','CAMUS/EchoNet有公开申请入口；贴片长视频与参考、元数据待确认','代码地址或数据入口不等于已取得下载权限或已完成复现','矩阵X列与计划书3节'],
 ['更新建议','每轮导师讨论后','补充全文、指南条款、JCR截图/导出与真实数据条件，再更新V0.2','优先解决证据和测量前提，再增加模型数量','正式引用前再核对学校参考文献格式']
]
sheet('检索记录',['类别','范围/主题','检索式/来源/内容','口径与限制','核查线索'],queries,[24,34,112,112,45],88)

# Calculate all narrative row heights from actual content so wrapped text remains visible.
for s in wb.worksheets:
    for row in s.iter_rows(min_row=2):
        maxlines=1
        for c in row:
            if c.value is None:continue
            width=s.column_dimensions[c.column_letter].width
            text=str(c.value)
            weighted=sum(2 if ord(ch)>255 else 1 for ch in text)
            maxlines=max(maxlines,math.ceil(weighted/max(width-2,1)))
        s.row_dimensions[row[0].row].height=max(s.row_dimensions[row[0].row].height or 0,maxlines*15+12)
    s.print_area=s.dimensions

xlsx=OUT/'心脏贴片超声_20篇文献与研究计划.xlsx'
wb.save(xlsx)

# Build editable Word documents directly as standard OOXML (no library install required).
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
def wtext(text):return escape(str(text))
def run(text):return '<w:r><w:t xml:space="preserve">'+wtext(text)+'</w:t></w:r>'
def para(text,style='Normal'):
    return f'<w:p><w:pPr><w:pStyle w:val="{style}"/></w:pPr>{run(text)}</w:p>'

# Preset: narrative_proposal. Named academic overrides: A4; Chinese Songti 12pt,
# 1.5 line spacing; black headings with SimHei; compact title masthead.
def style(name,size,before,after,line=360,bold=False,color='222222',keep=False,align='both',east='宋体'):
    flags=('<w:keepNext/>' if keep else '')+'<w:widowControl/>'
    return f'''<w:style w:type="paragraph" w:styleId="{name}"><w:name w:val="{name}"/>{'<w:basedOn w:val="Normal"/>' if name!='Normal' else ''}<w:pPr>{flags}<w:spacing w:before="{before*20}" w:after="{after*20}" w:line="{line}" w:lineRule="auto"/><w:jc w:val="{align}"/></w:pPr><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="{east}"/><w:sz w:val="{size*2}"/><w:szCs w:val="{size*2}"/><w:color w:val="{color}"/>{'<w:b/>' if bold else ''}</w:rPr></w:style>'''
styles='''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="'''+W+'''"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体"/><w:sz w:val="24"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:widowControl/><w:spacing w:line="360" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>'''
styles+=style('Normal',12,0,8)
styles+=style('Title',20,0,6,300,True,keep=True,align='left',east='黑体')
styles+=style('Subtitle',12,0,10,300,color=GREY,keep=True,align='left')
styles+=style('Heading1',16,18,10,300,True,keep=True,align='left',east='黑体')
styles+=style('Heading2',13,12,6,300,True,keep=True,align='left',east='黑体')
styles+=style('Heading3',12,8,4,300,True,keep=True,align='left',east='黑体')
styles+=style('Reference',10,0,6,280,align='left')
styles+=style('Header',9,0,0,240,color=GREY,align='left')
styles+=style('Footer',9,0,0,240,color=GREY,align='right')
styles+='</w:styles>'
# Encode semantic outline levels explicitly.
for name,level in [('Heading1',0),('Heading2',1),('Heading3',2)]:
    start=styles.index(f'w:styleId="{name}"');end=styles.index('</w:style>',start)
    part=styles[start:end].replace('<w:pPr>','<w:pPr><w:outlineLvl w:val="'+str(level)+'"/>',1)
    styles=styles[:start]+part+styles[end:]

rels='''<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/><Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/></Relationships>'''
rootrels='''<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/></Relationships>'''
content='''<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/><Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/><Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/><Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/><Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/></Types>'''
section='''<w:sectPr><w:headerReference w:type="default" r:id="rId2"/><w:footerReference w:type="default" r:id="rId3"/><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="708" w:footer="708"/><w:cols w:space="720"/><w:docGrid w:linePitch="360"/></w:sectPr>'''
footer=f'''<?xml version="1.0" encoding="UTF-8"?><w:ftr xmlns:w="{W}"><w:p><w:pPr><w:pStyle w:val="Footer"/></w:pPr>{run('第 ')}<w:fldSimple w:instr="PAGE"/>{run(' 页')}</w:p></w:ftr>'''
settings=f'''<?xml version="1.0" encoding="UTF-8"?><w:settings xmlns:w="{W}"><w:zoom w:percent="100"/><w:defaultTabStop w:val="420"/><w:updateFields w:val="true"/><w:compat/></w:settings>'''

def build_doc(kind,filename):
    d=D[kind];body=para(d['title'],'Title')+para(d['subtitle'],'Subtitle')
    body+=para('编制日期：2026年11月7日｜依据：现有毕业设计任务书｜设备与数据：尚未确定','Subtitle')
    if kind=='review':
        body+=para('使用说明：文内[1]—[20]与Excel编号一致。本文为可修改的开题初稿；部分依据摘要，具体核验状态见文献矩阵。正式提交前补齐全文精读、指南条款和学校格式。')
    else:
        body+=para('使用说明：以下为相对16周计划；先执行公开数据路线，真实贴片验证以数据和参考条件到位为前提。文内编号与配套Excel及文献综述一致。')
    for sec in d['sections']:
        body+=para(sec['heading'],'Heading1')
        for p in sec['paragraphs']:body+=para(p)
    body+=para('参考文献（与Excel编号一致）','Heading1')
    body+=para('采用顺序编码的参考文献草稿；已保留DOI。在线先发日期与卷期年不同者，以卷期年列参考条目，在线日期见Excel。最终按学校要求统一为GB/T 7714或指定格式。','Reference')
    for p in P:body+=para(f"[{p['id']}] {p['citation']}",'Reference')
    xml=f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="{W}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:body>{body}{section}</w:body></w:document>'''
    hdr=f'''<?xml version="1.0" encoding="UTF-8"?><w:hdr xmlns:w="{W}">{para('心脏贴片超声研究 · '+('文献综述' if kind=='review' else '研究计划'),'Header')}</w:hdr>'''
    core=f'''<?xml version="1.0" encoding="UTF-8"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>{wtext(d['title']+' '+d['subtitle'])}</dc:title><dc:subject>毕业设计开题准备</dc:subject><dc:creator>研究工作稿</dc:creator></cp:coreProperties>'''
    target=OUT/filename
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for name,data in {'[Content_Types].xml':content,'_rels/.rels':rootrels,'word/document.xml':xml,'word/_rels/document.xml.rels':rels,'word/styles.xml':styles,'word/header1.xml':hdr,'word/footer1.xml':footer,'word/settings.xml':settings,'docProps/core.xml':core}.items():z.writestr(name,data.encode('utf-8'))
    return target

doc1=build_doc('review','文献综述_初稿V0.1.docx')
doc2=build_doc('plan','研究计划书_初稿V0.1.docx')

# Reopen exports for compact, deterministic QA.
check=load_workbook(xlsx,data_only=False)
assert check.sheetnames==['阅读导航','文献矩阵','期刊指标','参数与边界','执行计划','检索记录']
assert check['文献矩阵'].max_row==21 and len({check['文献矩阵'].cell(r,20).value for r in range(2,22)})==20
assert all(isinstance(check['文献矩阵'].cell(r,9).value,(int,float)) for r in range(2,22))
assert all(isinstance(check['文献矩阵'].cell(r,11).value,datetime.datetime) for r in range(2,22))
assert not any(str(c.value) in ['#REF!','#DIV/0!','#VALUE!','#NAME?','#N/A'] for s in check for row in s for c in row)
ns={'w':W}
docstats=[]
for target in [doc1,doc2]:
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        for n in z.namelist():
            if n.endswith(('.xml','.rels')):ET.fromstring(z.read(n))
        root=ET.fromstring(z.read('word/document.xml'))
        texts=[''.join(p.itertext()) for p in root.findall('.//w:p',ns)]
        refs=[t for t in texts if re.match(r'^\[\d+\] ',t)]
        assert len(refs)==20
        assert all(p['doi'] in ''.join(texts) for p in P)
        docstats.append({'file':target.name,'paragraphs':len(texts),'characters':sum(map(len,texts)),'references':len(refs),'xml':'PASS','visual':'NOT RENDERED; LibreOffice unavailable'})

# Spreadsheet QA previews use the actual reopened exported cell values, widths,
# fills, and wrapped rows. These previews are internal, not an Excel-native render.
font_path='C:/Windows/Fonts/msyh.ttc'
def font(size):return ImageFont.truetype(font_path,size)
def wrap(draw,text,f,maxwidth):
    out=[]
    for paragraph in str(text).split('\n'):
        line=''
        for ch in paragraph:
            if draw.textlength(line+ch,font=f)>maxwidth and line:out.append(line);line=ch
            else:line+=ch
        out.append(line)
    return out
def render_part(s,cols,rstart,rend,name):
    widths=[int(s.column_dimensions[get_column_letter(c)].width*7.2) for c in cols]
    fs=14; f=font(fs);fh=font(fs)
    dummy=ImageDraw.Draw(Image.new('RGB',(1,1)))
    matrix=[]; heights=[]
    for r in [1]+list(range(rstart,rend+1)):
        lines=[]
        for c,width in zip(cols,widths):
            value=s.cell(r,c).value
            if isinstance(value,datetime.datetime):value=value.strftime('%Y-%m-%d')
            lines.append(wrap(dummy,'' if value is None else value,fh if r==1 else f,width-16))
        matrix.append((r,lines)); heights.append(max(44,max(len(x) for x in lines)*21+16))
    im=Image.new('RGB',(sum(widths)+2,sum(heights)+52),'white');draw=ImageDraw.Draw(im)
    draw.text((8,8),f'{s.title}  |  行{rstart}–{rend}  |  导出后内容核查',font=font(18),fill='#173B55')
    y=48
    for (r,all_lines),height in zip(matrix,heights):
        x=0
        for c,width,lines in zip(cols,widths,all_lines):
            fill='#173B55' if r==1 else ('#F1F6F8' if r%2==0 else '#FFFFFF')
            draw.rectangle((x,y,x+width,y+height),fill=fill,outline='#D8E3E9')
            for k,line in enumerate(lines):draw.text((x+8,y+7+k*21),line,font=fh if r==1 else f,fill='white' if r==1 else '#22313F')
            x+=width
        y+=height
    im.save(QA/name)
    return name

previews=[]
for s in check:
    if s.title=='文献矩阵':
        for label,cols in [('题录',list(range(1,14))),('分析',list(range(14,20))),('来源',list(range(20,25)))]:
            for start in [2,7,12,17]:previews.append(render_part(s,cols,start,min(start+4,21),f'矩阵_{label}_{start}.png'))
    else:previews.append(render_part(s,list(range(1,s.max_column+1)),2,s.max_row,f'{s.title}.png'))

report={'date':'2026-11-07','papers':20,'journals':len(M),'workbook':{'sheets':check.sheetnames,'unique_doi':20,'date_numeric_types':'PASS','required_fields':'PASS','formula_errors':0,'native_render':False,'preview_count':len(previews)},'documents':docstats,'previews':previews,'style_preset':'narrative_proposal with named academic overrides: A4, Songti 12pt/1.5; SimHei black headings; compact masthead'}
(QA/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='previews'},ensure_ascii=False,indent=2))
print('Final files:',*[x.name for x in OUT.iterdir()],sep='\n')
