# 独立一致性核查

这是三份独立审阅冻结后的单独核查层，不是第四份审稿报告。核查未回传审阅者，结果不自动计作审阅共识。数值依据见 [numeric_audit.json](numeric_audit.json)，可用 [audit_frozen_results.py](audit_frozen_results.py) 重复本次保存结果复算。复算只读取冻结资料及经来源校验的原掩膜，不训练、不推理、不改图、不更改计算口径。

最终发布前再次核对报告锁和输入锁。可读报告补发的技术经过见发布质检记录，补发未得到其他人的意见或本轮核查发现。

## AUD-01 队列与实验单位

- status 为 `passed`。
- claim_pointer 为 Fig.1、Table 1 的队列与固定划分。
- evidence_pointer 为 packet/snapshot/configs/camus_splits.json 及 1,000 个患者切面 sidecar，numeric_audit.json 的 cohort。
- check 为按患者核对归属、按切面核对视图／帧数和相序，不将帧数当独立样本数。
- result 为 500 患者、1,000 序列、19,232 帧，训练／验证／测试 347／71／82，测试 164 序列、3,167 帧。全部 ROI 仍为未人工审阅。21 个原始逆相序片段分别为训练 17、验证 1、测试 3。
- impact 为主要分母和划分一致。ROI 未审阅状态不能因本轮自动核对而改写。
- resolution_test 为保持当前患者分组和实际审阅状态；未来数据按受试者独立。
- reviewer_overlap 为审阅者均关注分母和参考层级；精确逆相序总数亦由 R3-m2 指出。

## AUD-02 保存掩膜与分割指标

- status 为 `passed`。
- claim_pointer 为 Fig.2、Table S2 与冻结 summary 的空间指标。
- evidence_pointer 为 runs/camus_cuda_progress 的原预测、CAMUS 原坐标专家掩膜、各 sidecar 标定和 Table S2 源表。
- check 为独立执行声明的最近邻坐标恢复，逐帧计算交集／并集、Dice、IoU 和物理边界距离，再按患者汇总。绝对与相对容差均为 1e-9。
- result 为 328 标注帧全部一致。患者级 Dice 0.9119086690、IoU 0.8416190524、ASSD 1.9627407936 mm、HD95 4.8113820694 mm；738 个患者分层记录与45组汇总一致。
- impact 为主要分割数字能从保存掩膜重现。均值 Dice 与均值 IoU 不应直接套单帧代数换算；当前实现已正确逐帧计算。
- resolution_test 为未来按同样单位和明示的边界距离定义评价新方法。
- reviewer_overlap 为 R2、R3 复算过源表，本轮另从原保存掩膜复算；这不改写为审阅者做过同样的像素级核查。

## AUD-03 功能点估计与置信区间

- status 为 `passed`。
- claim_pointer 为 Table 2、Table S1 的全部适用功能结果。
- evidence_pointer 为冻结 function.csv、两个表的 agreement_pairs.csv 和 agreement_statistics.csv。
- check 为从490行患者／方法／视图输出重建21组、1,712个有效配对，独立标量复算 MAE、RMSE、bias、LOA、r、预测 R²；另以声明的2,000次患者bootstrap、种子2026复算五行主MAE区间。
- result 为所有已查数字一致。负的 SV R² −0.00237、同法 EF R² −0.04113 均正确保留。标签EF的MAE 9.0320 pp、bias +1.5615 pp、LOA −20.1527 至 +23.2756 pp 一致。
- impact 为没有发现这些主统计抄录或算术错误。负 R² 不是需要修掉的格式问题。LOA 是差值的描述性界限，不是临床接受阈值或置信区间。
- resolution_test 为保持全部配对和原始有效 n；未来指定主要终点与患者级不确定性。
- reviewer_overlap 为 R2、R3 独立核对点统计；本轮bootstrap复算是单独核查。

## AUD-04 两种历史 bootstrap 记录

- status 为 `passed`。
- claim_pointer 为原 summary 和当前投稿表的 MAE 区间末位不同。
- evidence_pointer 为 packet/snapshot/src/visualization/analysis.py 的 agreement、旧 analysis_manifest.json 的 bootstrap 与当前 Table 2 图注。
- check 为先确认次数、种子、单位和配对数据，再比较点估计及区间。
- result 为原摘要用1,000次，现投稿图表沿用后来冻结的2,000次患者bootstrap；该区别已有说明，点估计和有效患者数相同。
- impact 为随机区间末位不同有明确来源，不能误判成结果篡改。
- resolution_test 为引用时标明所用版本，不在同一主结果中混放两套区间。
- reviewer_overlap 为本项作为数值核查结论单独保留，不要求三位审阅者都指出。

## AUD-05 几何与参考差异

- status 为 `passed`，含已确认的测量解释限制，不代表通过解剖有效性验证。
- claim_pointer 为单平面公式、同法参考与 S7 的偏倚关系。
- evidence_pointer 为历史 geometry.py、当前 mask_features.py／volume.py、全部3,167帧标量、S6及S7源表。
- check 为按 A 与 L 复算 V=8A²/(3πL)/1000，并核对同一82人的有符号均值关系。
- result 为公式数值一致，−5.8113485340 + 7.3728145809 = +1.5614660469 pp。单平面使用完整清理面积与较短代理轴，盘径只在该代理轴区间采样，空间支持范围存在已披露差异。
- impact 为同一几何的预测与专家轮廓比较不能排除共享定义偏差。容积路径比还受公式和视图差异影响，不能把它直接称为漏失容积比例。代数相加不构成因果分解，MAE也不能相加。
- resolution_test 为目标论文独立核验测量对象、人工解剖依据与临床参考；不能按本测试集优化几何。
- reviewer_overlap 为 R1-M1、R2-M3 与 R3-M1 对同一根问题形成独立共同关切。

## AUD-06 相位顺序、可用性及 null

- status 为 `passed`。
- claim_pointer 为 S2、S8、S9和完整功能表的覆盖率与失败原因。
- evidence_pointer 为原 frames.csv、function.csv、sequence_ledger.csv、unpaired_metrics.csv 和各测试 sidecar。
- check 为逐序列重放“全段最大值，再取其后最小值”的原规则，不逆转、不改选、不补值。
- result 为164序列有162个自动输出；两条4CH逆相序最大值在末帧而无后续ES。另一个逆相序 patient0217_2CH 虽有自动输出，相位仍不等于专家端点。patient0072_2CH 的ESV大于EDV，SV／EF保持null。总计10条缺失指标记录均有原因。HR／CO均为空。
- impact 为可用率不能解释为正确相位率或有效监测率。原始顺序和缺失已如实保留。
- resolution_test 为新的完整周期验证同时报告正确性、尝试数、有效覆盖与失败，不能仅追求输出数字的比例。
- reviewer_overlap 为各报告覆盖记录均涉及这些边界；具体共识按最终稳定ID映射。

## AUD-07 Table 1 的时间方向文字

- status 为 `confirmed_internal_error`，仅指局部文字与元数据矛盾。
- claim_pointer 为 Table 1 图注 “Sequence duration is the observed ED-to-ES interval”。
- evidence_pointer 为冻结 caption_en.md 和全部1,000个 sidecar 的 ED／ES 索引。
- check 为确认 `(frame count−1)/FPS` 的含义并核对原始相序。
- result 为21条片段按ES到ED存储，故统一称为ED到ES的经过时间不准确；正时长数值本身没有错误。
- impact 为读者可能误认为全队列均是按收缩方向排列。没有证据表明作者反转、拼接或伪造过数据。
- resolution_test 为下轮把该句改成观测半序列首末帧时长或ED／ES端点间隔，并说明原始顺序；不更改数值或顺序。本轮未改图。
- reviewer_overlap 为 R2-m1、R3-m2。

## AUD-08 重复表达及样本数

- status 为 `passed`。
- claim_pointer 为 R2／R3 的直径数据与十张历史分析图的证据数量。
- evidence_pointer 为 R2 frame_diameters.csv 与 R3 observed_vertices.csv，以及旧图源表。
- check 为逐行比较720个直径，核对独立患者和图件身份。
- result 为R2与R3完全相同，是两位患者的36帧×20个轴位置；曲面并未增加独立实验。十张旧图主要重用同一冻结实验，已明确属历史表达。
- impact 为这是已披露、可接受的备选表达，不是证实的重复发表或复制错误；正文需避免把它们累计为独立证据。
- resolution_test 为R2／R3择一承担相同论证，或明确主文与补充的互补作用。
- reviewer_overlap 为 R2、R3均指出同数据备选身份。

## AUD-09 历史代码、权重与预处理身份

- status 为 `passed`，范围限已查来源和静态执行路径。
- claim_pointer 为主结果来自哪个模型／配置，以及是否能把当前预处理逻辑追认为旧实验行为。
- evidence_pointer 为原summary、experiment.json、training.csv、run.json、权重SHA256，prepared_provenance.json及 audit_support/preprocessing_eefbd61.py。
- check 为核对164序列对应实验、训练／验证／测试患者集合、30轮最低验证BCE与权重哈希；另从数据预处理记录所指的eefbd61提交读取实际代码。
- result 为历史测试83f4489、模型camus_cuda_progress、选模epoch7、权重b0e8b724…一致；当前默认camus_regularized_v2不是该测试身份。历史预处理从影像估计support，标签用于几何变换和审计计数，不用于选择影像support。不能将当前代码的可选标签保留保护分支当成历史执行过的逻辑。
- impact 为现有信息不支持认定历史测试发生该类标签泄漏。ROI人工复核仍未完成。
- resolution_test 为下轮方法表绑定完整实验身份；重新处理数据时另存版本并保留坐标／标签审计。
- reviewer_overlap 为版本命名见报告记录；预处理代码的这项独立核查不追认审阅者已做过。

## AUD-10 全流程与临床复现的限度

- status 为 `not_assessable`。
- claim_pointer 为是否已经重新训练、重新推理并独立复验全部采集与临床链路。
- evidence_pointer 为本轮操作范围和共同包所含材料。
- check 为区分保存结果复算、重新模型推理、完整原始数据预处理、临床／贴片采集复验。
- result 为本轮完成保存掩膜和统计复算，核对1,422个不同原来源文件及1,371个包内锁文件；未做重新训练／推理、全量原始预处理或临床采集复验。
- impact 为不能把工程检查或本轮复算称为完成临床验证。作者后续表示可获得贴片与独立参考，并不等于这些数据已在本包。
- resolution_test 为新增实验解释之前，先锁定可执行实验入口，并验证旧checkpoint／对应流程能重现已有主要输出；若这一复现关口失败，应先定位来源问题，再解释新结果。
- reviewer_overlap 为审阅者均明确了其自身可评估范围；本轮范围独立记录。

## AUD-11 效率与设备能力

- status 为 `provenance_gap`，针对拟作标准化部署性能主张时的证据。
- claim_pointer 为是否可以用历史总耗时推断贴片端实时能力。
- evidence_pointer 为历史评价总耗时149.85 s与3,167帧，以及目前未提供的标准化延迟记录。
- check 为区分总处理吞吐与纯模型推理、端到端采集／传输／成像／分析延迟。
- result 为21.13 FPS只是总帧数除以历史总耗时的描述，不能据此得到独立模型ms／帧或真实设备端延迟。现有正文没有把它当成已完成部署验证。
- impact 为目标论文若提出实时性，需要新测量；当前不存在必须修改的FPS算术错误。
- resolution_test 为在实际设备与声明处理链上记录预热、批大小、输入尺度、硬件、持续运行、吞吐和端到端延迟。
- reviewer_overlap 为保留为面向目标论文的单独核查，不制造“共同发现”。

## AUD-12 历史训练损失的汇总层级

- status 为 `aggregation_ambiguity`，针对图中Mean BCE尚未解释的批次汇总层级。
- claim_pointer 为S3与历史训练图的轮次损失。
- evidence_pointer 为 historical/83f4489/cardiac/model.py第149至175行及R1-m2。
- check 为确认先计算每批mean BCE，再以各批次等权平均形成轮次日志。
- result 为284张验证帧、batch size 8时有35个完整批次及1个4帧批次，末批每帧对轮损失的权重为完整批次每帧的两倍。现日志与其执行规则一致，不等于全部像素严格等权平均。
- impact 为应解释统计层级，不能据此推断换成帧加权后一定改变epoch7或断言原模型选择有错。
- resolution_test 为下轮标明历史汇总规则；若未来改变规则，单独冻结新协议，历史曲线与选模标记不追溯修改。
- reviewer_overlap 为R1-m2单独提出，不计为审阅共识。

## 本轮解释

没有发现上述主表点统计和已声明置信区间的算术错误。确认的一处内部表述问题是AUD-07。解剖几何、独立功能标准、完整周期及真实贴片外部验证仍是目标论文需要解决的实质证据关口。两类结论必须同时保留，不能用数值复算通过替代方法和临床有效性，也不能因验证尚缺而否定已正确计算的基线结果。
