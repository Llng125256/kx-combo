#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K线导演·复刻监控（自研引擎 + 模拟持仓，纯文本状态页）

【v1.7.37 2026-10-16 发版】期满真破位卡停留 1 天下架（交易分析团队主管席终裁批准；三席意见：多头驳回/空头批准/主管批准附条件——上线前置条件=验收 📋近日出清面板 完整展示近7日全部结局）：EXPIRE_LINGER 1→0，恢复 v1.7.25 旧行为（期满卡当日即出清、不挂卡），结局可见性由 v1.7.33 📋出清面板（近7日全部结局滚动展示）承接。纯展示层，判定/账本/候选环零接触。
【v1.7.30 2026-10-14 修复】顶替血缘旧卡状态标注修复（用户 10-14 指出 MUUUSDT 死卡标「持有中·浮盈-12.1%」误导观看者——10-07 信号观察期已满按纪律已死；交易分析团队双席辩论 bull22:bear21 + 研究主管蔡定锋终裁；纯展示层，判定/账本/候选环零接触）：
  (a) 状态读取源切换——supersede 血缘旧卡状态从候选环 exit_date（工程取证 9/9 全 None=坏源）改读与卡面同源的 sig 展示层状态（analyse 返回 sig_by_day 按 (sym,day) 索引全量信号含出清卡）；删除「无 exit_date 即渲染持有中」默认分支；
  (b) 状态词四态收敛（终裁矩阵）：live(含复活在仓)→「持有中·浮盈%·距到站%」（原样）｜⚠️破位观察中→「⚠️破位观察中·浮盈%」（无距到站）｜⛔brk_expire/复活后再破(killed)→「⛔真破位·已离场（模拟仓口径）·浮盈—·距到站—」｜✅dead/flag→「✅行程已走完·已平·浮盈—·距到站—」；
  (c) 安全网（空头席设计采纳）——状态不可判定/sig 缺失→中性渲染「顶替 MM-DD 旧卡：锚X/止损Y」不输出状态字段，绝不回退「持有中」默认值；_sig_post killed（复活后再破被杀卡）补挂展示标记（纯展示元数据）。
【v1.7.27 2026-10-13 22:5x 发版】页面开头新增红色系统性质声明（用户拍板）：右偏型趋势跟随系统/约46%交易被止损打掉(平均-7.66%)是必然的数学结果不是系统坏了/利润来自右尾(30天硬顶+32%/趋势终结+11%)/不敢扛浮亏手动干预止损不该用本系统。纯展示层。
  【v1.7.26 2026-10-13 21:4x 发版】横幅新增「扛单口径回测」事实行（用户问能否赚钱→三口径回测+交易分析团队终裁落地展示）：追卡片现价短线无超额（+5日 −0.27%）如实标注；回踩锚位进场+扛单（到站/趋势终结/30天硬顶，含资金费）均值+4.05%（幸存者0.7折+2.83%、验证期+2.44%）如实标注；纯展示层，引擎逻辑/账本零改动。
  【v1.7.29 2026-10-14 发版】跟单视图纪律位修复（用户 10-14 TEM/ORCL 案例指出；投资大师专家团 5 票会诊裁定——塔勒布/芒格/德鲁肯米勒/帕布莱/达摩达兰一致判「设计盲区非故意，P0 立即止血」；纯展示层，判定/账本/回测取数口径零改动）：
  (a) 架构原则（芒格升格）——任何新信息的展示，不得降低旧仓关键信息可达性；禁入/孤星是附加徽标不是替换状态，文本页与 HTML 禁入分支统一为「禁入（grade|lay 不满足开仓条件）｜原状态 advice」，advice 不再被 continue 丢弃（对齐 v1.7.14⑦ HTML 侧先例，文本页侧漏修本次补齐）；
  (b) 顶替明示——展示信号顶替同标旧候选时，新卡附旧卡血缘「顶替 MM-DD 旧卡：锚X/止损Y·持有中·浮盈N%·距到站N%／已平·理由 ret%｜展示位替换≠加仓指令，旧仓按原纪律管理」（旧卡=day 严格早于新信号的最近一条候选；候选补 dead_px 信号日定格死锚作展示元数据，判定逻辑不读）；旧卡在仓时文本页动词「买入→在册监控」（德鲁肯米勒：旧仓存活期禁出加仓暗示；测试套件不断言卡片动词，已核）；
  (c) advice 公共化——state_advice(x, cd) 单源实现，文本页/HTML/禁入三分支零漂移。
  入册未进本版（v1.8.0 候选）：持仓台账面板与信号流物理分离（帕布莱/达摩达兰/塔勒布）、持仓驱动硬状态机（塔勒布根因修复）、死锚 ATR 口径手术式修改+触站收盘价判定（达摩达兰，判定层需预注册）、ATR 膨胀期死锚衰减/效率退出（塔勒布/德鲁肯米勒）、孤星日 1.5% 阈值回溯校准（德鲁肯米勒）。
  【v1.7.25 2026-10-13 15:1x 发版】期满真破位卡结局停留（用户提案「期满别无声消失」，交易分析团队双席辩论 bull8:bear7 终裁）：⚠️观察期满未收复的卡不再瞬间消失，停留 1 天（EXPIRE_LINGER=1，置0回退旧行为）展示结局红旗「⛔真破位·期满已离场（模拟仓口径）」+建议行「已按纪律出清，本卡仅作结局展示」——纯事实陈述无祈使句（v1.7.22(e) 假文案教训+非投资建议免责下禁动作指令，双席共识否决用户原话「请立即离场」措辞）；排序归🏁出清组不占⚠️风控置顶（避免假警报）；归🏁组与 FLAG_LINGER=5 天先例对齐。模拟账本零影响（期满当日已记已平）。
【v1.7.24 2026-10-13 14:2x 发版】G路径企稳备注诚实化（用户拍板「修并且发版」）：「（数日企稳确认+吞没）」改为「（入场形态·触轨MM-DD后数日企稳确认+吞没）」——备注是信号出生时的形态描述、不随后市涨跌更新，URNM 破位卡顶「数日企稳确认」被误读为当前状态系展示语义缺陷；现在明确「入场形态」前缀+触轨日期，杜绝误读。复活分支 note 本就带日期语义无歧义，不动。纯文案改动，引擎逻辑/账本/测试零触碰。
【v1.7.23 2026-10-13 12:5x 发版】展示层六项裁决（研究主管终裁，候选环过滤/账本行为零改动）：\n  E1 评分周一干净桶×1.3立即启用——信号日为周一且前两根bar均未触轨（nan保护）记 mon_clean，信号环普通/G路径与候选环同口径打标；score_of 层系数乘子顺序=批量1.2→周一1.3→周日0.5，合成层封顶1.8（裁决封顶）；\n  E2 在册排序锁死：⚠️置顶(risk)→状态分组(1持有/2✅到站/3🏁离场(dead+flag同有归3)/9禁入沉底)→-评分→-盈亏比rr→-新鲜度(_idx新→旧，analyse不再pop _idx)→字母序；HTML禁入卡沉底不变；\n  E3 数据不足卡展示层直算（裁决A）：同日候选缺失时按信号字段直算止损距离/仓位/杠杆（周日照旧减半），废除「（数据不足）」占位，文本页与HTML卡同步，过宽照旧放弃并标注；\n  E4 HTML企稳备注独立成行：card 增 sig_note 形参，各信号卡/模拟仓卡传 x['note']，note div 内 advice 后换行独立展示；\n  E5 页面读法文案更新（⚠️置顶先处理→主信号卡唯一分级（评分含周一桶×1.3，标签≠推荐强度）→入场区/追高→✅默认走→🏁挪仓→禁入沉底勿捡），文本页与HTML横幅同步；\n  E6 影子观察统计行：从 sym_cands 全部已平候选聚合周一干净桶与G路径 n/胜率/均值，n=0桶略去，文本页置「约束：」后、HTML置页脚免责上一行（标签≠推荐强度）。
  【v1.7.22 2026-10-13 10:4x 发版】健康度大审整改版（交易分析团队双席辩论空头45:多头35，裁决「可用但需整改」，用户拍板全部实施）：\n  (a/b)「再破即离场」口径统一与诚实化——原死分支（文案承诺路径代码不存在）按语义修正规解：「再破」=复活后再破：展示机维持 breaks≥2 杀卡原语义、账本机从「重置观察期再等3天」改为「立即离场」（从严统一，废除双机不一致）；观察期内持续破位不另算（连续阴跌≠二次事件），期满自然离场；文案同步改诚实（「期满未收复即离场，复活后再破立即离场」）；(i)硬顶可观测——模拟仓卡加「持仓 N/30 天」+⏳硬顶将至标注；(c)堵归类泄漏——AI科技桶补关键词（存储/晶圆/传感器等13词，未分类桶同日≤1系既有 CAP_SECTOR_DAY 覆盖，删除审计发现的冗余检查）；(d)⚡环境标签冻结于信号日（修老卡漂移）；(e)无牌信号不再显示「模拟仓已按风控口径离场」假文案；(f)⚡环境乘数停用回退×1.00基线（98.4%信号乘数=1.00且强=反向减仓）；(g)批量层加成1.5→1.2；\n  (h)横幅新增「规则全历史战绩（诚实口径）：N笔/胜率/均值/中位」行+在册卡溢价标注幸存者快照——主口径切换为合并口径（裁决：决策依据诚实性优先）。\n  【v1.7.21 2026-10-13 09:3x 发版】修复硬顶死代码（工程测试席 S8 发现+用户拍板修）：候选扫描窗 n−HARD_CAP→n−2×HARD_CAP（解耦窗口/硬顶基准），硬顶退出 j−i0≥30 恢复可达；30-60天龄信号自此以「硬顶退出」已平仓身份入账本（不再随窗口被动蒸发），展示层不变（已平仓不上卡）；账本胜率/均值将计入这批负贡献信号（更真实）。行为语义与 D-Audit 拍板一致，仅让既定硬顶真实生效。\n  【v1.7.20 2026-10-13 02:4x 发版】用户拍板纯减法版：①CCI 深度标签(CCI≤-175)彻底删除——🥇金标/「深度标签」文本/评分2.0档全部移除，主信号(下影>40%)成为唯一分级（D-Factor v2.0 终审：928因子在超额收益+聚类bootstrap+两期CI严格口径下零存活，v1的65个过筛系市场漂移+名义p假象；深度标签全年54.5%弱于主信号58.3%且梯度双期反向）。②原计划三因子标注全部不上线（D-Factor v2.0 阴性结论）。③账本内原 🥇 深度信号自此按 🥈 主信号档位（轻仓）处理。\n  【v1.7.19 2026-10-13 01:3x 发版】D-Audit v1.0 审计处置（用户拍板）：①硬顶 60→30 天回撤（扛单指纹双期坐实）②下影40%保留（邻域局部最优）③EMA10 保留不改（EMA8/ATR14 预注册 2026-11 复验）④CCI≤−175 深度标签降级为纯展示（全年 54.5% 弱于主信号 58.3%，「最强子集」未复现；是否改 −150 待终审）⑤死区 0.3×ATR 预注册事件驱动路径回放补审计 ⑥周线趋势赋能正式关闭 ⑦30-60天龄陈旧信号将随硬顶回撤从页面/账本消失（账本统计口径变化如实记录）。
  【v1.7.18 2026-10-12 21:5x 发版】更新频率改版（用户拍板）：定时轮 4→6 轮/天（00:35/04:35/08:35/12:35/16:35/20:35，每4小时，08:35保留为权威定版轮），页面头部文案同步；引擎逻辑/破位判定/离场判定零改动，纯时点与文案变更。
  【v1.7.17 2026-10-12 20:5x 发版】模拟仓占位案（交易分析团队 bull 26 vs bear 50，裁决 B 维持同标不重叠）：展示语义修复三项——①模拟仓卡 note 改仓位自描述（开仓日/现浮/止损），废除引用其他信号建议的错位写法 ②同标跳过事实可见化（N次/最近日期/有牌k次，账本 skip_detail 上送渲染）③新信号卡交叉标注「已有模拟仓，仅在册展示不入账」。账本规则零改动。
  【v1.7.16 2026-10-12 20:3x 发版】用户要求周日信号醒目化：卡片标签位新增大红色「🚫周日·降权0.5·复评中」标注（#ff3b30，独立 span，不占用⚠️破位/有效止损等文本），文本页信号行同步加前缀；澄清：周日裁决为「降权0.5+预注册复评」非「禁止买入」，若用户拍板升格禁买另行裁决。合成场景 26/26（新增 T3 sun_half 旗标、T4b 红标与破位⚠️并存）。
  【v1.7.15 2026-10-12 发版】用户 LRCX 截图质疑 + 交易分析团队裁决（多头 27 分 vs 空头 47 分，研究主管裁定）：
  ①周六新信号下册——展示与模拟账本均不再收周六(UTC)生成的信号（全池回测 n=100 双口径全面负期望：+5日 42%/−1.04%、引擎退出 26.4%/−1.32%；
    10-10 批量日周一 11/12 破位卡集中于周六=「批量日加成依赖工作日机构接力资金」的机理反例）。
    硬性回归项：周五及更早信号的破位/到站状态机照常消费周六日 K 线（合成场景 T1 验证）。
  ②周日信号降权 0.5 + 卡片标注「周日信号·权重0.5·复评中」（n=26 不足以定罪亦不足满权）。
    预注册复评规则：引擎退出口径样本 n≥60 或满一季度（先到者）期望仍负→自动下册不再辩论；期望转正→恢复权重 1.0。
  ③展示层对齐：信号卡新增「有效止损」= 止损 − 0.3×ATR（隐藏死区透明化；LRCX 10-08 收盘跌破显示止损但在死区内 4 天未认定的口径差修复）。
  ④文案如实化：「止损纪律优先」→「确认破位·2日观察期（0.3×ATR 容差+收盘确认，收上信号区上沿即复活）」。
  ⑤口径提示：自本版起周六历史候选不入页面账本与展示（独立回测数据通道不受影响）；全池 12 张破位观察卡零漏检复核——机制未丢破位，纯透明性问题。
  【v1.7.14 2026-10-12 待发】模拟账本收复参考线由死锚价(EMA10+ATR)改为信号区上沿(EMA10-ATR)，与展示机统一（用户质疑+研究主管裁决+三变体回测：C 均值+2.38%/PF1.64 vs A +1.58%/1.46；代价=真破位离场更深-7.57% vs -5.57%，最差单笔相同-32.1%可接受；加严变体(连续2日收复)+1.92%/1.54 备选未采纳）。复活重定级进账本（裁决④）需盘中改仓逻辑与独立回测，留待下一批。⑥HTML信号卡note补入信号自带备注（数日企稳确认/收复恢复等，此前只显示引擎建议——17:35首跑验收时发现的展示缺口）。⑦禁入卡沉底展示+备注保留破位观察信息+带观察卡标签亮⚠️（用户截图 KORU 指出：无牌信号带⚠️时被排到最前且信息被禁入文案覆盖，双 bug）。
  【v1.7.13 2026-10-12 待发（等技术团队审查）】①haos反向加权：强共振实测唯一亏损子集(PF0.90,n=175)
  却持1.2倍加成，改强×0.80/弱×0.90/无·超买×1.00 ②展示重构：金银铜→主信号(下影>40%)/深度标签(CCI≤-175)，
  仅深CCI组(+2.01%)经双口径回测证实为A口径副产品，标签仅展示 ③破位口径统一：模拟账本止损与展示机一致
  （容忍1次+2天观察+收复信号区上沿复活），旧「1次即离场」回测证伪（胜率38.1%→47.4% 均值+1.20%→+1.56%），
  观察期出场747笔全部为首破后2天未收复，二次确认0笔 ④G路径(启明星/跨K线确认)：瘫脚触轨后3日内企稳阳柱
  （中间仅十字星/小实体）正式成信号，止损=确认日最低，n=1191 均值+1.44% PF1.41 ⑤_simulate 共用推演函数
  提取（回归29只零漂移）。
  【v1.7.12 2026-10-12】牌级架构重构（用户拍板+金融团队裁决+全池回测验证）：①硬顶 30→60 天（均值+0.76%→+0.94%，PF1.19→1.23，让🏁离场机制接管时间砍仓）②🥈下影阈值 50%→40%（n+255，均值+1.43% vs +1.33%，四档平坦低过拟合）③🥇CCI阈值 -150→-175（修口径后-175最优PF1.23；-250均值转负，钻石档方向证伪）④🥉（10日跌>10%）剔除——全表垫底PF1.09~1.21⑤新成员制=下影>40%（主信号）或 CCI≤-175（深度标签），仅深CCI组实测最强子集(+1.99%/PF1.52)；动态升降级（触轨后3日最深定级）回测三项全弱于静态版，否决封存。全部基于2025-06-01+真实数据窗口、干净口径（剔>8%止损+资金费+同标不重叠）。
  【v1.7.11 2026-10-12】热修：卡片页横幅胜率格式错误（笔数误格式化为百分比显示 900%），改为 win/n_closed 口径与文本页一致。
  【v1.7.10 2026-10-12】热修：purge 清单补入 status/view.html——v1.7.9 暴露 view.html 从不刷缓存、用户最长看 12h 旧页的交付缺陷（一行修复）。
  【v1.7.9 2026-10-12】view.html 升级为卡片版 UI（丁导K线交易系统，用户定稿）：信号卡与模拟仓卡同款字段（锚/止损/死锚出场/距止损/仓位/杠杆/信号区/日期/现浮），CCI 不再上页面（引擎逻辑零改动，仅渲染层）；文本页四文件口径不变。
  【v1.7.0 2026-10-11】推荐即模拟持仓（专家团联合设计，用户拍板）：
  · 评分排序 = 分级分 × 当日层分 × 威廉环境分（全部实测值映射）
      分级 🥇2.0/🥈1.6/·1.1（v1.7.12起无🥉）；层 批量1.5/常规1.0/孤星禁入；环境 强1.2/弱1.0/🥈弱0.8
  · 档位决策表（v1.7.12起无🥉）：🥇批量=重/中仓，🥈批量=中/轻，🥇常规/🥈常规=轻，
    孤星一律禁入，无牌禁入（样本<30的格子按最差邻近处理）
  · 仓位：重10%/中6%/轻3% 名义；杠杆=风险预算÷(名义×止损距离)，封顶5×；
    风险预算 重1.0%/中0.6%/轻0.3%；止损距离<1.5%按1.5%计，>8%放弃信号
  · 止损=死区下沿+收盘确认（5规则回测帕累托最优：+1.35%，2×ATR方案-10.7%被否）
  · ✅走默认留例外（留须斜率>0+收盘>EMA10+量比>0.8）；✅后连续2日站稳EMA10→止损上移保本
  · 优先级 ⚠️>🏁>✅>30天硬顶；每轮重算只输出单一当前建议，旧建议自动隐藏
  · 【金融团队审计 2026-10-11】①模拟仓确认失败离场（到站后2日确认中收盘≤EMA10→当日平，
    命名「✅确认失败离场」，比设计默认走更早锁盈属保守化）②⚠️破位三确认≥1回填设计
    ③展示「⚠️观察中」时若模拟仓已离场→标注「模拟仓已按风控口径离场」④免责补两句
  ⑤模拟账户<100笔标注「样本不足，不构成有效性证据」
  · 行业分散：name括号解析→因果链归组，同大类≤2只/≤20%，同大类同日新开≤1只；
    解析失败进「未分类」桶同受约束；宽基ETF单列不计行业但计总敞口
    （v1.7.39 暂缓执行——无行业数据源，TODO 待接入行业分类后恢复）
  · 熔断（v1.7.39 中间态单档·账本机真执行）：并发≤8、单票≤10%、总敞口≤50%、
    杠杆=风险预算÷止损距离≤5×、止损距离>8%放弃入场；常量单源（pos_size/portfolio_admit）
  · 模拟盘=规则化全量模拟（每条合格信号必开仓、全约束），无幸存者偏差；
    资金费按0.01%/8h粗扣；跌穿止损按实际收盘记亏不美化
  · 市况横幅置顶：孤星日明示「今日不适合抄底」
  【破位口径（v1.7.13 统一）】模拟仓止损已与展示破位机统一：容忍 1 次确认破位
  （2 天观察 + 收复信号区上沿复活），观察期满或再次确认破位才离场。旧口径（1 次即离场）经
  回测证伪（胜率 38.1%→47.4%、均值 +1.20%→+1.56%、中位 −2.34%→−0.40%），历史分歧废弃。
  两处逻辑仍需同步检查。
  【v1.6】卖出并入买入行：✅死锚到站 / 🏁EMA10离场线 / ⚡威廉环境 / 终局驱动展示
  【v1.2】破位/收复状态机：容差0.3×ATR+三确认（爆量/瘫脚/CCI）
  【v1.0】Lucy=肯特纳双轨触及；🥇CCI<-150+收盘位>0.3（样本外验证：仅近期市场状态有效）
  公式搜索结论（2026-10-11）：8候选企稳公式无一通过替换及格线，CCI守位。
"""
from __future__ import annotations

import base64
import logging
import os
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import requests
import html
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kx_client import KxClient  # noqa: E402

RED_TXT = "右偏型趋势跟随系统:进场→按趋势持有→严格纪律出场。约46%交易会被止损打掉(平均-7.66%)=必然的数学结果,不是系统坏了;利润来自拿得住的右尾(30天硬顶+32%/趋势终结+11%)。不敢扛浮亏/手动干预止损=不该用本系统。月月盈利、回撤浅、胜率高=任何真实交易系统都不可达(顶级CTA同样有深回撤,趋势策略胜率普遍不到45%),稳定的印钞机这个标准更是不存在"
__version__ = "1.7.42"    # v1.7.42: 两项废除令（用户验收 2026-10-16，仅代码+本地测试，未上传未发版）：①废除下影>0.4主信号判定（交易三席终裁 agent-0d6d0908）——_sig_post 恢复定级 sh_r>0.4 复活门与触轨/候选环 shadow>0.4 分级代码路径删除，收复即复活、全信号 ·级；G 路径启明星形态判定（在册机制）零接触 ②废除🥈主信号分级（交易三席终裁 agent-7f2a447d）——TIER_MAIN=1.0 全信号统一乘子、TIER_POS 8/6/4%→单档6%（CAP_TICKER=0.10 硬顶兜底超限截断不递补，衔接 v1.7.39 风控层）、推荐口径=「通过全部禁入门槛的信号全集」（原「主信号子集」）、🥈徽标停用（渲染函数 tag_of 整体停用，卡面每日重推导、存量卡自然出清消化；⚠️/⛔/🆕/⏳/⚡ 标记通道不受影响）、·级无警示卡剔除规则停用；翻案判据=批量日≥30样本p<0.05且样本外通过    # v1.7.41: 取消入场cp>0.3过滤（用户验收2026-10-16，主管席终裁agent-f80e6cea，CI闸门+0.726pp/CI[0.116,1.361]下界>0/7季全正；翻案判据=滚动30票优势<0.5pp即回退）：账本机候选环入场判定=触EMA10−ATR14下轨即成立，删除 cp<=0.3 过滤（tests/prereg_cp_ci.md 预注册+tests/cp_ci_gate.py 闸门通过）；破位机三确认的cp<0.3（出场侧瘫脚判定）与展示机G路径零接触；冷却/扫描窗/周六/只买新卡/批量日/孤星禁入/评分分层v1.7.40定版全保留    # v1.7.40: 评分分层与仓位映射定版（用户验收 2026-10-16，三席终裁 agent-f067a173，翻案判据见交接件）：主信号评分乘子1.6→1.1、无牌1.1→1.0（TIER_MAIN/TIER_DOT 单源），环境乘子强1.2/弱1.0 等全部封存=1.0（ENV_MULT 单源）；仓位映射 10/6/3%→8/6/4%（TIER_POS 单源，pos_size 兜底同源复用）；判定/候选环零接触    # v1.7.39: 中间态风控层真执行进账本机（用户验收 2026-10-16，风控层定版：中间态单档）：模拟仓准入与仓位规则=并发≤CAP_CONCURRENCY(8)/单票名义≤CAP_TICKER(10%)/总敞口≤CAP_GROSS(50%)/杠杆=风险预算÷止损距离≤MAX_LEV(5×)/止损距离>MAX_STOP(8%)放弃入场，常量集中定义单源化（pos_size+portfolio_admit 唯一出处，展示层 direct_calc/常规卡同源复用）；行业分散暂缓——无行业数据源（sector_of 关键词启发式不可靠），CAP_SECTOR*/行业限额块停用并标注 TODO 待接入行业分类后恢复；60 交易日观察期条款（单日DD>20%降杠杆50%/PF<1.0停机/期满PF≥1.3转正）监控指标（交易日进度/单日最大DD/PF）在文本页尾部+HTML页脚输出。判定/候选环零接触    # v1.7.38: 保险丝盘中-only（用户验收 2026-10-16，主管席终裁：盘中触及即走）：_simulate/_sig_post 保险丝判定由「收盘触及」改「盘中 low[j]<=fuse_px 即触发」，离场价=触丝价 fuse_px（按触丝价成交，非收盘价）；forming bar 隔离（v1.7.36 止于最后完整交易日）保留不动；翻案判据=样本外崩盘测试盘中版 maxDD 未优于收盘版或滑点损失>1pp 即回调收盘版    # v1.7.38(前置): ⛔结局红旗标签文案修复（保险丝≠期满）：文本页+HTML 标签此前只判 brk_expire 硬编码「期满已离场」，v1.7.34 起保险丝结局卡（触锚×0.8 后2日内离场）全部错挂期满文案——新增 brk_red_tag 单源按 exit_kind 分流（fuse→⛔保险丝触发·已按纪律出清 / 默认→期满），advice 层判定不动（线上取证 exit_kind 已正确落上）。纯展示层，判定/账本/候选环零接触    # v1.7.37: 期满真破位卡停留 1 天下架（交易分析团队主管席终裁批准，三席：多头驳回/空头批准/主管批准附条件）：EXPIRE_LINGER 1→0，恢复 v1.7.25 旧行为（期满即出清不挂卡）；结局可见性由 📋近日出清面板（v1.7.33）承接，上线前置条件=验收出清面板完整展示近7日全部结局。纯展示层，判定/账本/候选环零接触    # v1.7.36: forming bar 退出卡龄链路（xbi 卡龄标注闪断修复）：末根bar日期=now_day(UTC)判定为当日进行中bar，卡龄 _age 与 _sig_post 破位状态机/复活/期满/死锚🏁判定一律止于最后一个完整交易日 lc_idx——修复晚间拉取含forming bar导致的①卡龄漂移±1（🆕↔卡龄N天边界抖动）②held_old/brk_expire 随盘中价翻转→badge 显示/消失闪断（xbi 实测：forming close 上穿旧卡收复线→旧卡被复活出清→四态矩阵读「持有中」→held_old→🆕消失；盘中午后回落/次日完整收盘→翻转回显示）。与冻结规格「止损只看收盘」「保险丝收盘触及」口径一致；now_day=None 行为与旧版逐位一致（向后兼容）。纯展示层，判定/账本/候选环零接触    # v1.7.35: 撤销v1.7.34深破加速线（交易分析团队真agent复核：多头席全桶无优势+空头席参数脆弱+V3在案警示），保留保险丝无条件生效；箱体页另挂诚实声明    # v1.7.34: 破位观察期深破加速线+保险丝无条件生效（用户拍板2026-10-15，13512事件分桶数据背书，spec=verdict_v6_bombardment.md§7）：①观察期内收盘<显示止损−1.5×ATR→立即离场(⛔深破加速止损)不等期满 ②保险丝(锚×0.8)收盘触及无条件生效(⛔保险丝)——修复ASTS穿丝仍干等漏洞。展示机同步brk_expire结局。判定依据=深破桶697笔(2天制-1.45%≈d1.5-1.52%打平，缩短持刀时间)    # v1.7.33: 📋 近日出清面板（用户拍板 2026-10-15，panel_spec 冻结规格）：近7个交易日全部出清结局（⛔破位/🏁趋势终结/✅到站/⏹硬顶/⚖️保本/❌确认失败）滚动展示，文本页尾部+HTML 底部独立 section，解决期满红旗卡一天蒸发的可见性盲区。纯展示层，判定/账本/候选环零接触    # v1.7.32: 卡龄标注上卡（用户拍板 2026-10-15，badge_spec 冻结规格）：每卡显示 🆕新卡(0-1交易日)/卡龄N天(2-4)/⏳老卡N天·新卡窗口已过(≥5)，文本页标签后+HTML卡主标签正下方同级；⛔期满卡与 held_old 豁免卡不显示。数据依据=卡龄课题 6803 笔配对回测（只买新卡终裁）。纯展示层，判定/账本/候选环零接触    # v1.7.31: 展示层整改（用户 ASTS 质询驱动+交易分析团队终裁）：①「有效止损」改名「收盘止损线」（语义诚实化：收盘跌破它才进观察期）②新增死区挣扎徽章（收盘∈[收盘止损线,止损) 时明示未确认破位照常持有）③新增保险丝单参考价=锚×0.8（券商挂单转换规则：盘中只防崩）④页头挂单规则行⑤期满红旗升权（用户拍板方案a）：被新信号顶替的期满卡同屏展示一天（归🏁出清组），期满次日自动出清——修复「期满红旗线上零出现」的可见性盲区。纯展示层，判定/账本/候选环零接触    # v1.7.30: 顶替血缘旧卡状态标注修复（交易分析团队双席辩论 bull22:bear21+研究主管终裁，用户拍板）：状态读取源从候选环 exit_date（9/9 全 None 坏源）改读与卡面同源的 sig 展示层状态（sig_by_day 全量传递），四态收敛矩阵+不可判定中性渲染安全网，判定/账本/候选环零接触    # v1.7.29: 展示层资本保全修复（投资大师专家团 5 票会诊裁定）：①架构原则——任何新信息的展示不得降低旧仓关键信息可达性；②孤星/禁入标注只追加不覆盖（文本页+HTML 双改， advice 不再被 continue 丢弃）；③顶替明示——新卡附旧卡血缘（日/锚/止损/状态/浮盈%/距到站%），旧卡在仓时动词降级「买入→在册监控」+「展示位替换≠加仓指令」防火墙    # v1.7.27: 页面开头新增红色系统性质声明（右偏趋势跟随/止损是数学必然）    # v1.7.26: 横幅新增扛单口径回测事实行（追现价无超额/锚位扛单正期望·含0.7折与衰减如实标注）    # v1.7.25: 期满真破位卡结局停留1天（红旗+归🏁出清组）
GH_API = "https://api.github.com/repos/Llng125256/kx-combo/contents"
FRESH_DAYS = 15
HARD_CAP = 30            # 信号/模拟仓硬顶（天）——v1.7.19 回撤（D-Audit v1.0 扛单指纹双期坐实：30天窗 60.8%/+1.74% vs 60天窗 52.5%/+0.25%，30-60天龄陈旧信号为负贡献；用户拍板 2026-10-13）
FLAG_LINGER = 5
EXPIRE_LINGER = 0        # v1.7.37: 期满停留下架（交易分析团队三席：多头驳回/空头批准/主管批准附条件），结局展示由📋出清面板承接（v1.7.33）；置1=回退v1.7.25停留1天行为
WORKERS = 16
BARS = 150
MAX_LEV = 5.0            # 杠杆封顶（=风险预算÷止损距离，≤5×；v1.7.39 单源）
MAX_STOP = 0.08          # 止损距离>8%放弃入场（v1.7.39 单源，原 STOP_FAR）
STOP_NEAR = 0.015        # 止损距离<1.5%按1.5%计
# v1.7.40 用户验收定版 2026-10-16，三席终裁 agent-f067a173，翻案判据见交接件
# v1.7.42 废除🥈主信号分级（用户验收 2026-10-16，主管席 agent-7f2a447d）：分级/梯度/仓位映射单档化，翻案判据=批量日≥30样本p<0.05且样本外通过
TIER_POS = {'中仓': 0.06}   # 仓位映射单源：名义占比单档 6%（v1.7.42 废除 8/6/4% 梯度）；CAP_TICKER=0.10 硬顶兜底——pos_size 内 min() 超限截断不递补，与 v1.7.39 风控层常量直接衔接
TIERS = {'中仓': (TIER_POS['中仓']*100, 0.6)}   # 名义%, 风险预算%（单档=原中仓 0.6 预算沿用）
TIER_MAIN = 1.0          # v1.7.42 废除（用户验收 2026-10-16，主管席 agent-7f2a447d）——🥈主信号评分乘子 1.1 废除→全信号统一 TIER=1.0（常量单源保留）；翻案判据=批量日≥30样本p<0.05且样本外通过
TIER_DOT = TIER_MAIN     # 无牌(·)乘子：v1.7.42 起与主信号同源同值（分级已废，全信号统一 1.0）
ENV_MULT = 1.0           # 环境乘子封存：强1.2/弱1.0 等全部=1.0（v1.7.22(f) 停用后的定版固化）
# ---- v1.7.39 风控层常量（中间态单档·单源化）：模拟仓准入与仓位规则唯一出处，pos_size/portfolio_admit 执行 ----
CAP_CONCURRENCY = 8      # 并发持仓上限（同时在仓≤8只）
CAP_TICKER = 0.10        # 单票名义占比上限（10%净值）
CAP_GROSS = 0.50         # 总敞口占比上限（50%净值）
CAP_TOTAL = CAP_GROSS * 100.0   # 总敞口%（兼容别名，单源=CAP_GROSS）
CAP_DAY_NEW = 3          # 同日新开
# TODO(行业分散·暂缓): 原 CAP_SECTOR=20%/CAP_SECTOR_N=2/CAP_SECTOR_DAY=1 及账本机行业限额块自 v1.7.39
# 停用——无行业数据源（sector_of 关键词启发式不可靠），待接入行业分类数据后恢复行业分散约束（用户验收 2026-10-16）
FUND_FEE_DAY = 0.0003    # 资金费 0.01%/8h ≈ 0.03%/天（名义占比）


def pos_size(tier, stop_dist, is_sun=False):
    """v1.7.39: 仓位/杠杆单源计算（中间态单档）——账本机/展示层（direct_calc、常规卡、HTML卡）唯一出处。
    名义 = min(档位基准, 风险预算÷止损距离, 单票上限 CAP_TICKER×100)；
    杠杆 = max(1, min(MAX_LEV, 风险预算÷(名义×止损距离)))；周日名义减半（杠杆上限不变）。
    返回 (notional, lev, reason)：reason 非 None = 放弃入场（当前仅止损距离>MAX_STOP）。"""
    if stop_dist > MAX_STOP:
        return None, None, '止损过宽'
    base, risk = TIERS.get(tier, (TIER_POS['中仓']*100, 0.6))   # v1.7.42: 兜底同源=单档（原轻仓兜底随梯度废除）
    notional = round(min(base, risk / stop_dist, CAP_TICKER * 100), 1)
    lev = round(max(1.0, min(MAX_LEV, risk / (notional * stop_dist))), 1)
    if is_sun:    # v1.7.15: 周日降权——名义减半（杠杆上限不变）
        notional = round(notional * 0.5, 1)
        lev = round(max(1.0, min(MAX_LEV, risk / (notional * stop_dist))), 1)
    return notional, lev, None


def portfolio_admit(active, sym, notional, day_new_n):
    """v1.7.39: 组合级准入单源（中间态单档）——同票不重叠、并发≤CAP_CONCURRENCY、
    总敞口≤CAP_GROSS、同日新开≤CAP_DAY_NEW。行业分散暂缓（无行业数据源，TODO 见常量区）。
    返回 None=准入；否则拒入原因字符串（skip_n 计数键）。"""
    if any(p['sym'] == sym for p in active):
        return '已有持仓'
    if len(active) >= CAP_CONCURRENCY:
        return '并发满'
    if sum(p['notional'] for p in active) + notional > CAP_GROSS * 100:
        return '总敞口满'
    if day_new_n >= CAP_DAY_NEW:
        return '当日限额'
    return None

SECTOR_KEYS = [
    ('宽基', ('ETF', '指数', '基金')),
    ('AI科技', ('半导体', '芯片', '光模块', 'AI', '算力', '数据中心', '云计算', '软件', '信息技术', '电子设计', '网络', '互联网', '存储', '内存', '晶圆', '设备', '测试', '传感器', '机器人', '智能', '数字', '科技', '技术', '数据')),
    ('汽车', ('汽车', '电动车', '整车', '自动驾驶')),
    ('医疗健康', ('医药', '生物', '医疗', '健康', '制药', '疗法', '诊断', '基因')),
    ('能源', ('石油', '天然气', '油气', '能源', '煤炭', '铀', '核能', '电力', '太阳能', '光伏', '新能源', '油田')),
    ('金融', ('银行', '保险', '证券', '金融', '支付', '交易所', '资管', '信贷')),
    ('消费', ('零售', '餐饮', '食品', '饮料', '咖啡', '服装', '消费', '家居', '电商', '旅游', '酒店', '度假', '博彩', '体育', '鞋', '啤酒', '美容', '化妆品', '宠物')),
    ('工业防务', ('航空', '航天', '国防', '军工', '防务', '机械', '制造', '工程', '建筑', '运输', '物流', '铁路', '卡车', '航运')),
    ('通信', ('电信', '通信', '运营商', '电话')),
    ('原材料', ('矿业', '稀土', '化工', '钢铁', '材料', '化肥', '造纸', '黄金', '白银', '铜', '铝')),
    ('媒体娱乐', ('媒体', '传媒', '影视', '流媒体', '游戏', '音乐', '视频', '娱乐')),
    ('房地产', ('房地产', '地产', 'REIT', '物业')),
]


def sector_of(name: str) -> str:
    """name 字段因果链归组：宽基最优先 → 关键词匹配 → 未分类。"""
    if not name:
        return '未分类'
    if 'ETF' in name or '指数' in name or '基金' in name:
        return '宽基'
    inner = name[name.find('（')+1:name.find('）')] if '（' in name and '）' in name else name
    text = inner + name
    for bucket, keys in SECTOR_KEYS:
        if bucket == '宽基':
            continue
        for kw in keys:
            if kw in text:
                return bucket
    return '未分类'


def ema(x, n):
    a = 2/(n+1); out = np.full(len(x), np.nan); out[0] = x[0]
    for i in range(1, len(x)): out[i] = a*x[i] + (1-a)*out[i-1]
    return out


def ema_nan(x, n):
    a = 2.0/(n+1)
    out = np.full(len(x), np.nan)
    idx = np.where(~np.isnan(x))[0]
    if len(idx) == 0: return out
    s = idx[0]; out[s] = x[s]
    for i in range(s+1, len(x)): out[i] = a*x[i] + (1-a)*out[i-1]
    return out


def wpr(high, low, close, n):
    hh = np.full(len(close), np.nan); ll = np.full(len(close), np.nan)
    for i in range(n-1, len(close)):
        hh[i] = high[i-n+1:i+1].max(); ll[i] = low[i-n+1:i+1].min()
    rng = hh - ll
    out = np.where(rng == 0, -50.0, (hh-close)/np.where(rng == 0, 1, rng)*-100.0)
    out[:n-1] = np.nan
    return out


def t3(x, n, v):
    e1 = ema_nan(x, n); e2 = ema_nan(e1, n); e3 = ema_nan(e2, n)
    e4 = ema_nan(e3, n); e5 = ema_nan(e4, n); e6 = ema_nan(e5, n)
    return (-v**3)*e6 + (3*v**2+3*v**3)*e5 + (-6*v**2-3*v-3*v**3)*e4 + (1+3*v+v**3+3*v**2)*e3


def haos_tag(high, low, close, fresh_days=FRESH_DAYS):
    """⚡强共振=双线当前≤-90；弱共振=仅慢线且进入≤15天。"""
    if len(close) < 120: return ''
    f = t3(wpr(high, low, close, 14), 3, 0.7)
    s = t3(wpr(high, low, close, 96), 3, 0.7)
    if np.isnan(f[-1]) or np.isnan(s[-1]): return ''
    if f[-1] <= -90 and s[-1] <= -90:
        return ' ⚡强共振'
    if s[-1] <= -90:
        j = len(close) - 1
        while j > 0 and not np.isnan(s[j-1]) and s[j-1] <= -90: j -= 1
        if (len(close)-1) - j <= fresh_days:
            return ' ⚡弱共振'
    return ''


def haos_tag_ob(high, low, close):
    """⚡超买共振：双线当前≥-10（止盈环境提醒）。"""
    if len(close) < 120: return ''
    f = t3(wpr(high, low, close, 14), 3, 0.7)
    s = t3(wpr(high, low, close, 96), 3, 0.7)
    if np.isnan(f[-1]) or np.isnan(s[-1]): return ''
    if f[-1] >= -10 and s[-1] >= -10:
        return ' ⚡超买共振'
    return ''



def _simulate(high, low, close, vol, ema10, atr, cci, n, dates, i0, ei, stop, dead, anchor, rec_ref=None):
    """持仓推演（v1.7.13 抽取为共用函数，逻辑与原内联逐字一致）:
    破位=统一容忍口径(首破进2天观察, 收上信号区上沿复活, 复活后再破=立即离场[v1.7.22 与展示机统一从严口径], 期满未收复离场) >
    到站三条件 > 保本 > 🏁趋势终结 > 硬顶(HARD_CAP, 自信号日 i0 起算)。
    返回 (exit_day, exit_px, reason)。"""
    rec_line = dead if rec_ref is None else rec_ref   # v1.7.14: 收复参考线
    fuse_px = anchor*0.8 if anchor is not None else None   # v1.7.34: 保险丝=锚×0.8
    exit_day, exit_px, reason = None, None, '在仓'
    hold, pend, cnt2 = False, 0, 0
    st_j, brk_j = 'live', None
    for j in range(ei, n):
        if np.isnan(atr[j]) or np.isnan(cci[j]): continue
        if fuse_px is not None and low[j] <= fuse_px:   # v1.7.38: 保险丝盘中触及即走（用户验收2026-10-16，主管席终裁：盘中-only），离场价=触丝价 fuse_px 非收盘价
            exit_day, exit_px, reason = j, fuse_px, '⛔保险丝'
            break
        pen = stop - close[j]
        if pen > 0.3*atr[j]:
            rng_j = high[j]-low[j]+1e-9
            cp_j = (close[j]-low[j])/rng_j
            vr_j = vol[j]/(vol[max(0, j-10):j].mean()+1e-9)
            if (vr_j > 3.0) + (cp_j < 0.3) + (cci[j] < -100) >= 1:
                if st_j == 'live':
                    st_j, brk_j = 'broken', j          # 首破：进入2日观察
                elif st_j == 'recovered':
                    # v1.7.22(b): 复活后再破=立即离场（与展示机 killed 同步，废除原「重置观察期再等3天」）
                    exit_day, exit_px, reason = j, close[j], '⚠️破位止损'
                    break
                # st_j=='broken'（观察期内持续破位）：不另算，期满自然离场（连续阴跌≠二次事件）
        if st_j == 'broken' and close[j] > rec_line:
            st_j = 'recovered'          # 收复信号区上沿=复活(v1.7.14)
        # v1.7.35: 深破加速线撤销（交易分析团队复核：多头席独立复算全桶无优势+空头席参数脆弱；V3在案警示一致）
        if st_j == 'broken' and (j - brk_j) > 2:
            exit_day, exit_px, reason = j, close[j], '⚠️破位止损'
            break
        if st_j == 'broken':
            continue    # 审查/Tessa修复: 观察期内破位优先级最高, 不评估到站/保本/🏁
        if not hold and high[j] >= dead:
            if pend == 0:
                slope_ok = (ema10[j]+atr[j]) > (ema10[j-1]+atr[j-1])
                ema_ok = close[j] > ema10[j]
                vr_ok = vol[j]/(vol[max(0, j-10):j].mean()+1e-9) > 0.8
                if not (slope_ok and ema_ok and vr_ok):
                    exit_day, exit_px, reason = j, close[j], '✅到站止盈'
                    break
                pend = 1          # 三条件过，进入连续2日站稳确认
                continue
            else:
                if close[j] > ema10[j]:
                    pend += 1
                    if pend >= 3:  # 到站日 + 2日确认
                        hold = True
                    continue
                else:
                    exit_day, exit_px, reason = j, close[j], '✅确认失败离场'
                    break
        if hold:
            if close[j] < anchor:
                exit_day, exit_px, reason = j, close[j], '保本离场'
                break
            cnt2 = cnt2+1 if close[j] < ema10[j] else 0
            if cnt2 >= 2:
                exit_day, exit_px, reason = j, close[j], '🏁趋势终结'
                break
        if j - i0 >= HARD_CAP:
            exit_day, exit_px, reason = j, close[j], '硬顶'
            break
    return exit_day, exit_px, reason



def _sig_post(sig, high, low, close, openp, vol, atr, cci, ema10, n, dates,
              d_i, lo_i, hi_i, dead_px, anchor_px=None):
    """展示层信号后处理（v1.7.13 自原内联块提取，普通触轨与 G 路径共用）:
    破位/收复状态机(容忍1次+2天观察+收复信号区上沿复活) > ✅死锚标记 > 🏁趋势终结(FLAG_LINGER 出清)。
    d_i=信号日下标; lo_i=止损线; hi_i=收复参考线(信号区上沿); dead_px=死锚出场价。
    返回 True=保留, False=出清。"""
    state, breaks, brk_j, rec_j = 'live', 0, None, None
    killed = False
    for j in range(d_i+1, n):
        if np.isnan(atr[j]) or np.isnan(cci[j]): continue
        # v1.7.38: 保险丝(锚×0.8)盘中 low 触及→⛔结局（与账本机同步，盘中-only）；live态触丝视为确认破位入观察流（v1.7.34a 堵永久滞留泄漏）
        if anchor_px is not None and low[j] <= anchor_px*0.8:
            sig['brk_expire'] = True; sig['exit_kind'] = 'fuse'
            if state != 'broken':
                state, brk_j = 'broken', j
            break
        back = close[j] > hi_i
        pen = lo_i - close[j]
        if state == 'broken' and back:
            state, rec_j = 'recovered', j
            continue
        if pen <= 0.3*atr[j]: continue
        rng_j = high[j]-low[j]+1e-9
        cp_j = (close[j]-low[j])/rng_j
        vr_j = vol[j]/(vol[max(0, j-10):j].mean()+1e-9)
        conf = sum([vr_j > 3.0, cp_j < 0.3, cci[j] < -100])
        if conf >= 1 and state != 'broken':
            # v1.7.22(b): 口径注释——「再破」=复活（recovered）后的再次确认破位 → breaks=2 杀卡；
            # 观察期内持续破位不另算（连续阴跌≠二次事件），期满自然离场。账本机已同步此口径。
            breaks += 1
            if breaks >= 2:
                killed = True
                sig['killed'] = True   # v1.7.30: 展示层元数据——复活后再破被杀卡（纯展示标注，判定逻辑不读；供 supersede 血缘标⛔）
                break
            state, brk_j = 'broken', j
    if killed: return False
    if state == 'broken':
        lag = (n-1) - brk_j
        if lag > 2 + EXPIRE_LINGER: return False    # v1.7.25: 停留 EXPIRE_LINGER 天后出清
        if lag > 2:
            sig['brk_expire'] = True    # v1.7.25: 期满真破位·结局停留日——不设⚠️观察警告（避免假警报位），改挂「⛔真破位·期满已离场」红旗并归🏁出清组
        elif not sig.get('exit_kind'):   # v1.7.34a(B②): fuse/deep 结局卡不挂 ⚠️观察中
            sig['warn'] = (sig['warn'] + f' ⚠️破位{dates[brk_j][5:]}观察中').strip()
    elif state == 'recovered':
        # v1.7.42 改动一（废除下影>0.4 主信号判定，交易三席终裁 agent-0d6d0908）：
        # 删除 sh_r=(min(close,open)−low)/(high−low)>0.4 的主信号判定代码路径——
        # 原逻辑=恢复日下影>40% 才定🥈复活，否则 return False 出清；现收复信号区上沿即复活，
        # 恢复卡一律 ·级（🥈分级同步废除=改动二）。G 路径启明星形态判定系另一套在册机制，未动。
        sig['grade'] = '·'
        sig['cci'] = cci[rec_j]
        sig['note'] = f"（{dates[rec_j][5:]}已收复）"
        if _is_sun(sig['day']):    # v1.7.15: 复活分支保留周日降权标注
            sig['note'] = '周日信号·权重0.5·复评中｜' + sig['note']
    sig['dead_px'] = round(float(dead_px), 2)
    dead_j = None
    for j in range(d_i+1, n):
        if high[j] >= dead_px:
            dead_j = j; break
    flag_j = None
    if dead_j is not None:
        sig['dead'] = f" ✅行程已走完({dates[dead_j][5:]})"
        cnt = 0
        for j in range(dead_j+1, n):
            cnt = cnt+1 if close[j] < ema10[j] else 0
            if cnt >= 2:
                flag_j = j
                sig['flag'] = f" 🏁趋势终结({dates[j][5:]})"
                break
    if flag_j is not None and (n-1) - flag_j > FLAG_LINGER:
        return False    # 🏁回看期满 → 出清
    return True


def analyse(sym, bars, now_day):
    """单标的：返回 (最新展示信号|None, 候选列表, 信号日集合, last_close)。

    候选 = 2×HARD_CAP(60) 天扫描窗内每个合格触及事件（硬顶 HARD_CAP 天退出，v1.7.21） + 单标的全生命周期推演
    （⚠️破位止损 > ✅走默认留例外 > 保本/🏁 > 30天硬顶；组合级约束由 main 叠加）。
    """
    if len(bars) < 40:
        return None, [], set(), 0.0, set(), {}
    dates = [str(b['time'])[:10] for b in bars]
    high = np.array([float(b['high']) for b in bars])
    low = np.array([float(b['low']) for b in bars])
    close = np.array([float(b['close']) for b in bars])
    openp = np.array([float(b['open']) for b in bars])
    vol = np.array([float(b.get('volume') or 0) for b in bars])
    n = len(bars)
    # v1.7.36: forming bar 不参与卡龄链路——末根bar日期=now_day(UTC)即为当日进行中bar，
    # 卡龄与破位状态机一律止于最后一个完整交易日 lc_idx（修复晚间拉取含forming bar导致的
    # 卡龄漂移±1与 held_old/brk_expire 随盘中价闪断；now_day=None 时行为与旧版完全一致）
    lc_idx = n - 1
    if now_day and dates[-1] == now_day:
        lc_idx = n - 2
    ema10 = ema(close, 10)
    tr = np.maximum(high[1:], close[:-1]) - np.minimum(low[1:], close[:-1])
    tr = np.concatenate([[high[0]-low[0]], tr])
    atr = np.full(n, np.nan)
    for i in range(14, n): atr[i] = tr[i-14:i].mean()
    tp = (high+low+close)/3
    cci = np.full(n, np.nan)
    for i in range(19, n):
        w = tp[i-19:i+1]; m = w.mean(); cci[i] = (tp[i]-m)/(0.015*np.abs(w-m).mean()+1e-9)
    cand_win = n - 2 * HARD_CAP    # v1.7.21: 候选扫描窗=2×硬顶，覆盖信号全生命周期（修复硬顶分支不可达：原 n−30 与 j−i0≥30 互斥，硬顶从未真实触发）
    f_t3 = t3(wpr(high, low, close, 14), 3, 0.7)
    s_t3 = t3(wpr(high, low, close, 96), 3, 0.7)

    def env_at(i):
        if np.isnan(f_t3[i]) or np.isnan(s_t3[i]): return '无'
        if f_t3[i] <= -90 and s_t3[i] <= -90: return '强'
        if s_t3[i] <= -90: return '弱'
        if f_t3[i] >= -10 and s_t3[i] >= -10: return '超买'
        return '无'

    sigs = []
    sig_by_day = {}   # v1.7.30: 展示层状态索引 {信号日: sig}——含被出清的卡（brk_expire/killed/🏁回看清零），供 supersede 血缘读取与卡面同源的旧卡状态
    candidates = []
    touch_days = set()
    last = -99
    for i in range(20, n-1):
        if np.isnan(ema10[i]) or np.isnan(atr[i]) or np.isnan(cci[i]): continue
        if not (low[i] <= ema10[i]-atr[i]) or i - last <= 2: continue
        rng_i = high[i]-low[i]+1e-9
        cp_i = (close[i]-low[i])/rng_i
        if cp_i <= 0.3:
            # v1.7.13 G路径(启明星/跨K线确认): 瘫脚触轨后3日内出现企稳阳柱
            # (中间仅十字星/小实体), 信号日=确认日j, 锚=确认日次日开盘, 止损=确认日最低。
            # 回测 n=1191 均值+1.44% PF1.41（主信号 n=1601 +2.16% PF1.70）。
            # 审查修复#1: G 触发时设 last(触轨去重)、受 hard 窗口约束、确认日计入 touch_days。
            for j in range(i+1, min(i+4, n-1)):
                body_j = abs(close[j]-openp[j])/(high[j]-low[j]+1e-9)
                cpj = (close[j]-low[j])/(high[j]-low[j]+1e-9)
                if close[j] > openp[j] and cpj > 0.3 and not np.isnan(cci[j]):
                    last = i                    # G 触发同计触轨去重（同一次下跌只记一次）
                    if i < cand_win: break      # v1.7.21: 超扫描窗触轨不产 G 信号
                    touch_days.add(dates[j])    # 确认日=真实买入触发日, 计入孤星/批量统计
                    if _is_sat(dates[j]): break    # v1.7.15: 周六新信号下册（市况统计仍计入）
                    g_g = '·'    # v1.7.42 改动二: 🥈主信号分级废除（用户验收 2026-10-16，主管席 agent-7f2a447d）——新信号不再打🥈；G 路径启明星形态判定本身保留（改动一边界）
                    anchor_j = float(openp[j+1])
                    stop_j = float(low[j])
                    dead_j = float(ema10[i]+atr[i])
                    engul = close[j] > openp[i]
                    sig_g = {'day': dates[j], 'side': 'buy', 'grade': g_g, '_idx': j,
                             'anchor': anchor_j, 'zone': f"[{low[i]:.2f}~{ema10[i]-atr[i]:.2f}]",
                             'cci': float(cci[i]), 'warn': '',
                             'note': f'（入场形态·触轨{dates[i][5:]}后数日企稳确认' + ('+吞没' if engul else '') + '）',    # v1.7.24: 备注明确为出生形态+触轨日期，防误读为当前状态（URNM 破位卡案例）
                             'haos': haos_tag(high[:j+1], low[:j+1], close[:j+1]) + haos_tag_ob(high[:j+1], low[:j+1], close[:j+1]),   # v1.7.22(🟠2): G 路径同步冻结信号日
                             'env': env_at(j), 'stop': stop_j}
                    sig_g['stop_eff'] = round(float(stop_j - 0.3*atr[j]), 2)    # v1.7.15
                    if _is_sun(dates[j]):
                        sig_g['note'] = ('周日信号·权重0.5·复评中｜' + sig_g['note']).strip('｜')    # v1.7.15
                        sig_g['sun_half'] = True    # v1.7.15
                    # v1.7.23: E1 周一干净桶——确认日(信号日)为周一、j>=2 且前两根 bar 均未触轨（nan 视为未触轨）
                    if _wd(dates[j]) == 0 and j >= 2:
                        _t1 = (not np.isnan(ema10[j-1]) and not np.isnan(atr[j-1])
                               and low[j-1] <= ema10[j-1]-atr[j-1])
                        _t2 = (not np.isnan(ema10[j-2]) and not np.isnan(atr[j-2])
                               and low[j-2] <= ema10[j-2]-atr[j-2])
                        if not _t1 and not _t2:
                            sig_g['mon_clean'] = True
                    # 审查修复#2: G 信号与普通信号同走展示后处理（破位状态机+✅+🏁出清）
                    _g_keep = _sig_post(sig_g, high, low, close, openp, vol, atr, cci, ema10, lc_idx + 1, dates,
                                        j, stop_j, ema10[i]-atr[i], dead_j, anchor_px=anchor_j)
                    sig_by_day[dates[j]] = sig_g   # v1.7.30: 无论去留全量登记（出清卡带 brk_expire/killed 状态供血缘读取）
                    if _g_keep:
                        sigs.append(sig_g)
                    sd_j = max(0.015, (anchor_j-stop_j)/anchor_j)
                    if sd_j <= 0.08:
                        ed, ep, rs = _simulate(high, low, close, vol, ema10, atr, cci, n, dates,
                                               i0=j, ei=j+1, stop=stop_j, dead=dead_j, anchor=anchor_j,
                                               rec_ref=ema10[i]-atr[i])
                        candidates.append({'day': dates[j], 'grade': g_g, 'env': env_at(j),
                                           'anchor': anchor_j, 'stop': stop_j, 'stop_dist': sd_j,
                                           'idx': j, 'n': n, 'src': 'G',
                                           'dead_px': round(float(dead_j), 2),   # v1.7.29: 信号日定格死锚（展示层元数据，供顶替明示的距到站%；判定逻辑不读）
                                           'mon_clean': bool(sig_g.get('mon_clean')),   # v1.7.23: E1 G 候选同口径 mon_clean（供影子统计）
                                           'exit_day': ed,
                                           'exit_date': dates[ed] if ed is not None else None,
                                           'exit_px': ep, 'reason': rs,
                                           'ret': (ep/anchor_j-1)*100 if ed is not None else None})
                    break
                elif body_j <= 0.3:
                    continue          # 十字星/小实体过渡, 允许
                else:
                    break             # 大实体非企稳 = 下跌中继, 放弃
            continue
        last = i
        if i < cand_win: continue    # v1.7.21: 扫描窗放宽至2×硬顶
        touch_days.add(dates[i])
        if _is_sat(dates[i]): continue    # v1.7.15: 周六新信号下册（市况统计仍计入）
        rng = high[i]-low[i]+1e-9
        cp = (close[i]-low[i])/rng
        vr = vol[i]/(vol[max(0, i-10):i].mean()+1e-9)
        c = cci[i]
        # v1.7.42 改动一+二（终裁 agent-0d6d0908 / agent-7f2a447d）: 删除 shadow=(min(close,open)−low)/(high−low)>0.4
        # 对主信号/主信号子集的构成作用——下影不再决定分级，全信号统一 ·级
        grade = '·'
        lo_i, hi_i = low[i], ema10[i]-atr[i]
        anchor = openp[i+1]
        sig = {'day': dates[i], 'side': 'buy', 'grade': grade, '_idx': i, 'anchor': anchor,
               'zone': f"[{lo_i:.2f}~{hi_i:.2f}]", 'cci': c,
               'warn': '', 'note': '', 'haos': haos_tag(high[:i+1], low[:i+1], close[:i+1]) + haos_tag_ob(high[:i+1], low[:i+1], close[:i+1]),   # v1.7.22(d): 环境标签冻结于信号日
               'env': env_at(i), 'stop': lo_i}
        sig['stop_eff'] = round(float(lo_i - 0.3*atr[i]), 2)    # v1.7.15: 有效止损=止损−0.3×ATR（死区透明化）
        # v1.7.23: E1 周一干净桶——信号日为周一、i>=2 且前两根 bar 均未触轨（nan 视为未触轨）
        if _wd(dates[i]) == 0 and i >= 2:
            _t1 = (not np.isnan(ema10[i-1]) and not np.isnan(atr[i-1])
                   and low[i-1] <= ema10[i-1]-atr[i-1])
            _t2 = (not np.isnan(ema10[i-2]) and not np.isnan(atr[i-2])
                   and low[i-2] <= ema10[i-2]-atr[i-2])
            if not _t1 and not _t2:
                sig['mon_clean'] = True
        if _is_sun(dates[i]):
            sig['note'] = ('周日信号·权重0.5·复评中｜' + sig['note']).strip('｜')    # v1.7.15
            sig['sun_half'] = True    # v1.7.15: 红色标注旗标（卡片标签位）

        _keep = _sig_post(sig, high, low, close, openp, vol, atr, cci, ema10, lc_idx + 1, dates,
                          i, lo_i, hi_i, ema10[i]+atr[i], anchor_px=anchor)
        sig_by_day[dates[i]] = sig   # v1.7.30: 无论去留全量登记（出清卡带 brk_expire/killed 状态供血缘读取）
        if not _keep:
            continue    # 破位观察期满/二次确认/🏁回看期满 → 出清
        sigs.append(sig)
    sigs.sort(key=lambda s: s['day'], reverse=True)

    # ---- 候选（模拟仓推演，单标的无约束口径）----
    last_c = -99
    for i in range(20, n-1):
        if np.isnan(ema10[i]) or np.isnan(atr[i]) or np.isnan(cci[i]): continue
        if not (low[i] <= ema10[i]-atr[i]) or i - last_c <= 2: continue
        # v1.7.41: 取消入场cp>0.3过滤（用户验收2026-10-16，主管席终裁agent-f80e6cea，CI闸门+0.726pp/CI[0.116,1.361]下界>0/7季全正；翻案判据=滚动30票优势<0.5pp即回退）——触下轨即成立入场，其余条件（冷却/扫描窗/周六/新卡/批量/孤星/分层）不变；破位机三确认的cp<0.3（出场侧）不动
        last_c = i
        if i < cand_win: continue    # v1.7.21: 扫描窗放宽至2×硬顶
        if _is_sat(dates[i]): continue    # v1.7.15: 周六新信号不入账本
        # v1.7.42 改动二: 🥈分级废除（agent-7f2a447d）——候选环 grade 仅作展示字段，不再参与分级/准入
        grade = '·'
        anchor = openp[i+1]
        stop = low[i]
        stop_dist = max(STOP_NEAR, (anchor-stop)/anchor)
        cand = {'day': dates[i], 'grade': grade, 'env': env_at(i), 'anchor': anchor,
                'stop': stop, 'stop_dist': stop_dist, 'idx': i, 'n': n, 'src': '触轨',
                'dead_px': round(float(ema10[i]+atr[i]), 2)}   # v1.7.29: 信号日定格死锚（展示层元数据，供顶替明示的距到站%；判定逻辑不读）
        # v1.7.23: E1 候选环同口径 mon_clean（供影子统计；本环过滤逻辑零改动）
        if _wd(dates[i]) == 0 and i >= 2:
            _t1 = (not np.isnan(ema10[i-1]) and not np.isnan(atr[i-1])
                   and low[i-1] <= ema10[i-1]-atr[i-1])
            _t2 = (not np.isnan(ema10[i-2]) and not np.isnan(atr[i-2])
                   and low[i-2] <= ema10[i-2]-atr[i-2])
            if not _t1 and not _t2:
                cand['mon_clean'] = True
        # 生命周期推演（统一容忍口径：⚠️首破观察2天+收复信号区上沿复活，观察期满/再破离场；✅默认走须三条件+连续2日站稳确认）
        exit_day, exit_px, reason = _simulate(
            high, low, close, vol, ema10, atr, cci, n, dates,
            i0=i, ei=i+1, stop=low[i], dead=ema10[i]+atr[i], anchor=anchor,
            rec_ref=ema10[i]-atr[i])
        if exit_day is not None:
            cand.update({'exit_day': exit_day, 'exit_date': dates[exit_day],
                         'exit_px': exit_px, 'reason': reason,
                         'ret': (exit_px/anchor-1)*100})
        else:
            cand.update({'exit_day': None, 'exit_date': None, 'exit_px': None,
                         'reason': '在仓', 'ret': None})
        candidates.append(cand)
    # v1.7.21(🟠1): 展示窗=硬顶窗——信号龄>HARD_CAP 的卡不上展示（它们必然已硬顶出清）
    # v1.7.23: E2 不再 pop _idx——保留供展示排序的新鲜度键（新→旧）；展示窗过滤语义不变
    sigs = sorted((s for s in sigs if (n - 1) - s['_idx'] <= HARD_CAP),
                  key=lambda x: x['day'], reverse=True)
    latest = sigs[0] if sigs else None
    for _s in sig_by_day.values():    # v1.7.32: 卡龄=交易日差，信号日定格供展示层 age_tag 消费；v1.7.36: 止于最后完整交易日
        if isinstance(_s, dict) and '_idx' in _s: _s['_age'] = lc_idx - _s['_idx']
    return latest, candidates, touch_days, close[-1], set(dates), sig_by_day   # v1.7.30: +sig_by_day 展示层状态索引


def push_summary(lines, webhook, snap_name):
    """企微精简推送（可选，默认关闭）：只推头部+模拟账户+在仓前5+⚠️/🏁行，不推全文。

    目的：jsDelivr 对固定文件名 purge 按路径限流（实测 throttlingReset≈598s），
    页面无法保证分钟级新鲜；推送走企微直达，不受任何 CDN 缓存影响。
    """
    head = lines[:6]
    acct = [l for l in lines if l.startswith('💼')][:1]
    pos = [l for l in lines if l.strip().startswith('▶')][:5]
    alert = [l for l in lines if ('⚠️破位' in l or '🏁' in l or '⛔' in l)][:5]
    body = "\n".join(head + ([""] + acct if acct else []) + (["", "▶ 在仓(前5):"] + pos if pos else [])
                     + (["", "⚡ 需处理:"] + alert if alert else ["", "（无⚠️/🏁告警）"])
                     + ["", f"完整页面: status/{snap_name}（带时间戳，永不缓存）"])
    try:
        r = requests.post(webhook, json={"msgtype": "text", "text": {"content": body[:3800]}},
                          timeout=15)
        print(f"[replica] 企微推送: {'OK' if r.status_code == 200 else f'HTTP {r.status_code}'}")
    except Exception as e:
        print(f"[replica] 企微推送异常: {e}")


def tier_of(grade, lay, env):
    """v1.7.42: 废除🥈主信号分级（用户验收 2026-10-16，主管席 agent-7f2a447d，翻案判据=批量日≥30样本p<0.05且样本外通过）。
    推荐口径=「通过全部禁入门槛的信号全集」单档中仓 6%；禁入门槛不变：孤星日禁入。
    grade/env 不再参与分级（🥈/· 差异废除），签名保留以兼容调用点。"""
    if lay == '孤星':
        return '禁入'
    return '中仓'    # v1.7.42: 全信号单档（原 🥈批量=中/轻、🥈常规=轻、无牌禁入 三分支删除）


def score_of(grade, lay, env, day=None, mon_clean=False):
    g = TIER_MAIN    # v1.7.42: 全信号统一乘子 1.0（🥈主信号分级废除，agent-7f2a447d；原 {'🥇':2.0,'🥈':TIER_MAIN}.get(grade,TIER_DOT) 删除）
    l = 1.2 if lay == '批量' else 1.0    # v1.7.22(g): 批量加成 1.5→1.2（行业性共振下跌中批量是同一次下跌的投影；同行业>5 失效条件留研究课题）
    if mon_clean:
        l *= 1.3    # v1.7.23: E1 周一干净桶 ×1.3（乘在层系数上；叠加顺序=先批量1.2→再周一1.3→封顶→再周日0.5）
    l = max(0.7, min(l, 1.8))    # v1.7.23: E1 合成层乘数封顶区间 [0.7,1.8]（只约束批量×周一合成；周日 0.5 为 v1.7.15 冻结独立乘数，在封顶之后叠加不受此区间约束）
    if day is not None and _is_sun(day):
        l *= 0.5    # v1.7.15: 周日信号降权 0.5（预注册复评：n≥60 或满一季度仍负→自动下册；v1.7.23 复核确认在封顶之后叠加）
    e = ENV_MULT    # v1.7.40: 环境乘子强1.2/弱1.0 等全部封存1.0（单源 ENV_MULT）
    return round(g*l*e, 2)


def direct_calc(x, tier):
    """v1.7.23: E3 同日候选缺失时按信号字段直算（展示层，裁决 A）。
    返回 (stop_dist0, notional, lev)；过宽时 notional/lev 为 None（调用方按放弃文案处理）。
    口径与常规卡一致：STOP_NEAR 下限、TIERS 档位公式、周日照旧减半、杠杆封顶 MAX_LEV（v1.7.39: 统一走 pos_size 单源，含单票≤CAP_TICKER）。"""
    stop_dist0 = max(STOP_NEAR, (x['anchor'] - x['stop']) / x['anchor'])
    notional, lev, sz_reason = pos_size(tier, stop_dist0, _is_sun(x['day']))    # v1.7.39: pos_size 单源
    if sz_reason:
        return stop_dist0, None, None
    return stop_dist0, notional, lev


def brk_red_tag(x):
    """v1.7.38: ⛔结局红旗标签单源（文本页+HTML 零漂移）——按 exit_kind 分流（触丝≠期满）：
    fuse→保险丝触发，默认→期满未收复。修复 v1.7.34 起保险丝结局卡复用期满标签的文案错位
    （exit_kind 字段在 _sig_post 已正确落上，标签渲染路径此前只判 brk_expire 未读 exit_kind）。"""
    if x.get('exit_kind') == 'fuse':
        return '⛔保险丝触发·已按纪律出清（模拟仓口径）'
    return '⛔真破位·期满已离场（模拟仓口径）'


def state_advice(x, cd=None):
    """v1.7.29: 状态 advice 公共提取——禁入分支复用，只追加不覆盖。
    架构原则（芒格裁决升格）：任何新信息的展示，不得降低旧仓关键信息可达性——
    禁入/孤星等全局状态是附加徽标，永远不得替换卡片自身的状态 advice。"""
    if x.get('brk_expire'):
        if x.get('exit_kind') == 'fuse': return '⛔保险丝触发·已按纪律出清（模拟仓口径），本卡仅作结局展示'
        return '⛔真破位·期满未收复，已按纪律出清（模拟仓口径），本卡仅作结局展示'
    if x.get('flag'): return '🏁离场：触发离场线，按纪律出局'
    if x.get('warn'):
        a = '⚠️确认破位·2日观察期：止损含0.3×ATR容差（见收盘止损线），收盘收上信号区上沿即复活，期满未收复即离场，复活后再破立即离场'
        if cd and cd.get('reason') == '⚠️破位止损': a += '（模拟仓已按风控口径离场）'
        return a
    if x.get('dead'): return '✅已到站：默认走；趋势健在则留并上移止损至锚价'
    return '持有中，等 ✅/🏁/⚠️'


def zone_badge(x, lc):
    """v1.7.31: 死区挣扎徽章（纯展示，ASTS 用户质询驱动）——收盘∈[stop_eff, stop) 时明示未确认破位。
    判定/账本零接触；warn/期满/已平等状态卡不重复标注。"""
    se, st = x.get('stop_eff'), x.get('stop')
    if (not lc or not isinstance(se, (int, float)) or not isinstance(st, (int, float))
            or x.get('warn') or x.get('brk_expire') or x.get('flag') or x.get('dead')):
        return ''
    if se <= lc < st:
        return f"🔻死区挣扎中: 收盘{lc:.2f}∈{se:.2f}~{st:.2f} 未确认破位, 照常持有"
    return ''


def fuse_px(x):
    """v1.7.31: 券商保险丝单参考价=锚×0.8（2026-10-14 交易分析团队终裁：盘中只防崩, 止损只看收盘）。纯展示。"""
    a = x.get('anchor')
    if not a:
        return '—'
    return f"{a*0.8:.2f}" if a < 1000 else f"{a*0.8:.1f}"


def row_sort_key(r, closes):
    """v1.7.23: E2 在册排序多键（锁死）：⚠️置顶 → 状态分组 → -评分 → -盈亏比rr → -新鲜度(_idx新→旧) → 字母序。
    分组：1=持有中(无dead无flag) 2=✅已到站(dead非空) 3=🏁离场(flag非空，dead+flag同有归3) 9=禁入沉底。
    rr=(dead_px-close)/(close-stop_eff)；任一缺失或 close<=stop_eff 时 rr=-999（排组内最后）。"""
    _, sym, x, _, _, tier, score = r
    risk = 0 if x.get('warn') else 1
    if x.get('brk_expire') or x.get('flag'):
        group = 3    # v1.7.25: 期满真破位停留卡归🏁出清组（不占⚠️风控位）
    elif x.get('dead'):
        group = 2
    elif tier == '禁入':
        group = 9
    else:
        group = 1
    close = closes.get(sym, 0)
    dead_px = x.get('dead_px')
    stop_eff = x.get('stop_eff')
    if dead_px is None or stop_eff is None or not close or close <= stop_eff:
        rr = -999.0
    else:
        rr = (dead_px - close) / (close - stop_eff)
    return (risk, group, -score, -rr, -x.get('_idx', 0), sym)



def _wd(dstr):
    """UTC 日期串 -> weekday()（0=周一..5=周六, 6=周日）。"""
    import datetime as _dt
    return _dt.date(int(dstr[:4]), int(dstr[5:7]), int(dstr[8:10])).weekday()


def _is_sat(dstr):
    return _wd(dstr) == 5


def _is_sun(dstr):
    return _wd(dstr) == 6


def age_tag(x):
    """v1.7.32: 卡龄标注（纯展示层，badge_spec 冻结规格 2026-10-15）——交易日口径 (n−1)−_idx；
    0-1=🆕新卡 / 2-4=卡龄N天 / ≥5=⏳老卡N天·新卡窗口已过；⛔期满红旗卡与 held_old 豁免卡不显示（防误导）。
    数据依据：卡龄课题 6803 笔配对回测（K5 −0.70pp/K10 −3.15pp，p=0.0000，年分段 100% 同号）"""
    if x.get('brk_expire') or x.get('held_old'): return ''
    a = x.get('_age')
    if a is None: return ''
    if a <= 1: return '🆕新卡'
    if a <= 4: return f'卡龄{a}天'
    return f'⏳老卡{a}天·新卡窗口已过'


REASON_EMO = {'⚠️破位止损': '⛔', '🏁趋势终结': '🏁', '✅到站止盈': '✅', '硬顶': '⏹', '保本离场': '⚖️', '✅确认失败离场': '❌'}   # v1.7.33
REASON_SHORT = {'⛔保险丝': '保险丝', '⚠️破位止损': '破位止损', '🏁趋势终结': '趋势终结', '✅到站止盈': '到站止盈', '硬顶': '硬顶', '保本离场': '保本', '✅确认失败离场': '确认失败'}   # v1.7.33
REASON_CLS = {'⚠️破位止损': 'red', '🏁趋势终结': 'grn', '✅到站止盈': 'grn', '硬顶': '', '保本离场': '', '✅确认失败离场': 'red'}   # v1.7.33


def collect_recent_exits(sym_cands, max_days=7):
    """v1.7.33: 📋 近日出清面板数据（纯展示层）——近 max_days 个交易日（按数据内实际出场日取最近7个不同日）的全部出清结局；
    (sym, day) 去重防触轨+G 同日碰撞；同日按收益升序（亏的先看）。返回 [{date,sym,reason,ret}] 按 date 新→旧"""
    seen, by_day = set(), {}
    for sym, cands in sym_cands.items():
        for c in cands:
            ed = c.get('exit_date')
            if not ed or c.get('ret') is None: continue
            key = (sym, c.get('day'))
            if key in seen: continue
            seen.add(key)
            by_day.setdefault(ed, []).append((sym, c['reason'], float(c['ret'])))
    if not by_day: return []
    days = sorted(by_day, reverse=True)[:max_days]
    out = []
    for ed in days:
        for sym, reason, ret in sorted(by_day[ed], key=lambda x: x[2]):
            out.append({'date': ed, 'sym': sym, 'reason': reason, 'ret': ret})
    return out


def exits_panel_text(exits, max_rows=40):
    """v1.7.33: 文本页面板行（纯展示）"""
    if not exits: return ["📋 近日出清: 近 7 个交易日无出清"]
    from collections import Counter
    cnt = Counter(x['reason'] for x in exits)
    head = (f"📋 近日出清（近7个交易日）: 共 {len(exits)} 笔（"
            + " ".join(f"{REASON_SHORT[k]}{v}" for k, v in cnt.most_common()) + "）")
    out = [head]
    for x in exits[:max_rows]:
        out.append(f"  {REASON_EMO.get(x['reason'], '·')} {x['sym']} {x['date'][5:]} {REASON_SHORT.get(x['reason'], x['reason'])} {x['ret']:+.1f}%")
    if len(exits) > max_rows: out.append(f"  （仅显示最近 {max_rows} 笔）")
    return out


def esc(s):
    return html.escape(str(s))


def tag_of(x):
    """v1.7.42: 🥈主信号标签停用（废除令 agent-7f2a447d）——「主信号子集」口径废除，
    推荐口径=「通过全部禁入门槛的信号全集」；标签恒 '—'，⚠️/⛔/🆕/⏳/⚡ 等其他标记不受影响
    （分属 warn/red_tag/age_tag/env 独立通道）。历史卡随信号日重推导自然出清消化。"""
    return '—'    # v1.7.42: 主信号(下影>40%)标签整体停用（原 x.get('main') 判定删除）


def render_html(rows, closes, open_pos, st):
    """卡片版 view.html（v1.7.9，丁导K线交易系统）。
    信号卡与模拟仓卡同款字段；纯渲染层，判定逻辑与文本页完全同源。
    v1.7.17: 模拟仓卡 note 改为仓位自描述+同标跳过事实可见化；信号卡交叉标注占位事实。"""
    open_map = {p['sym']: p['day'] for p in open_pos}    # v1.7.17
    skip_map = st.get('skip_by_sym') or {}               # v1.7.17
    G_COLOR = {'🥇': '#f5c542', '🥈': '#c0c7d1', '🥉': '#cd8b52', '·': '#8b93a1'}
    E_COLOR = {'强': '#6ea8ff', '弱': '#9aa4ff', '超买': '#ff9f43'}

    def zone_s(x):
        z = x.get('zone')
        if isinstance(z, (list, tuple)):
            return f"[{z[0]:.2f}~{z[1]:.2f}]" if len(z) == 2 else '~'.join(str(v) for v in z)
        return str(z) if z else '—'

    def dead_s(x):
        v = x.get('dead_px')
        return f"{v:.2f}" if isinstance(v, (int, float)) else '—'

    def advice_of(x, cd):
        # v1.7.29: 委托公共 state_advice——文本页/HTML/禁入分支三处文案零漂移（原内联双份维护）
        return state_advice(x, cd)

    def card(g, sym, env, live, score, anchor, stop, dead, sd, tier, pct, lev, zone, day, note, tag='—', stop_eff='—', red_tag='', sig_note='', fuse='—', badge='', agetag=''):    # v1.7.32: +agetag 卡龄标注（主信号标签同级，第一眼可见）
        gc = G_COLOR.get(g, G_COLOR['·'])
        env_html = f'<span class="env" style="color:{E_COLOR.get(env, "")}">⚡{env}共振</span>' if env else ''
        live_cls = 'grn' if (live or 0) >= 0 else 'red'
        return f'''<div class="card">
  <div class="card-h"><span class="tag" style="color:{gc}">{tag}</span>{f'<span class="tag" style="color:#ff3b30">{red_tag}</span>' if red_tag else ''}
    <b>{esc(sym)}</b> {env_html}
    <span class="live {live_cls}">{live:+.1f}%</span>
    <span class="score">评分 {score}</span></div>
  {f'<div class="tag" style="color:#ff9f43">{esc(agetag)}</div>' if agetag else ''}
  <div class="grid">
    <div><i>锚 Entry</i><em>{anchor}</em></div>
    <div><i>止损 Stop</i><em class="red">{stop}</em></div>
    <div><i>收盘止损线</i><em class="red">{stop_eff}</em></div>
    <div><i>保险丝单</i><em class="red">{fuse}</em></div>
    <div><i>死锚出场</i><em class="grn">{dead}</em></div>
    <div><i>距止损</i><em class="red">-{sd}%</em></div>
    <div><i>仓位</i><em class="grn">{tier} {pct}%</em></div>
    <div><i>杠杆</i><em class="grn">{lev}x</em></div>
    <div><i>信号区 Zone</i><em class="sm">{esc(zone)}</em></div>
    <div><i>{day[0]}</i><em>{day[1]}</em></div>
  </div>
  <div class="note">{esc(note)}{('<br>' + esc(sig_note)) if sig_note else ''}{(f'<br><span style="color:#ff9f43">{esc(badge)}</span>') if badge else ''}</div>
</div>'''

    sig_cards = []
    jin_cards = []   # v1.7.14: 禁入卡沉底展示（用户拍板：无仓位建议的卡不占前排）
    for _, sym, x, cd, lay, tier, score in rows:
        lc = closes.get(sym, 0)
        live = (lc / x['anchor'] - 1) * 100 if lc and x['anchor'] else 0.0
        anchor_s = f"{x['anchor']:.2f}" if x['anchor'] < 1000 else f"{x['anchor']:.1f}"
        se = f"{x['stop_eff']:.2f}" if isinstance(x.get('stop_eff'), (int, float)) else '—'    # v1.7.15 有效止损
        _rt_parts = []
        if x.get('sun_half'): _rt_parts.append('🚫周日·降权0.5·复评中')
        if x.get('brk_expire'): _rt_parts.append(brk_red_tag(x))   # v1.7.38: 按 exit_kind 分流（触丝≠期满）
        rt = ' '.join(_rt_parts)
        tag_d = ('⚠️' if x.get('warn') else '') + tag_of(x)   # 破位观察的卡在标签上直 visibly 亮 ⚠️
        _sup = f"｜{x['supersede']}" if x.get('supersede') else ''   # v1.7.29: 顶替血缘（旧卡日/锚/止损/状态/浮盈%/距到站%+非加仓防火墙）
        if tier == '禁入':
            # v1.7.29: P0 止血——禁入是附加徽标不是替换状态：卡片自身 advice 必须存活（TEM 案例：破位观察期纪律位被孤星禁入整块吞掉）
            note = advice_of(x, cd) + f"｜禁入（{x['grade']}|{lay}）{x.get('warn', '')}" + _sup
            jin_cards.append(card(x['grade'], sym, x.get('env', ''), live, score,
                                  anchor_s, f"{x['stop']:.2f}", dead_s(x), '—',
                                  '—', '—', '—', zone_s(x), ('信号日', x['day']), note, tag_d, stop_eff=se, red_tag=rt, fuse=fuse_px(x), badge=zone_badge(x, lc), agetag=age_tag(x),
                                  sig_note=x.get('note', '')))    # v1.7.23: E4 企稳备注独立成行
            continue
        if cd is None:
            # v1.7.23: E3 同日候选缺失——按信号字段直算仓位（展示层，裁决 A），废除「（数据不足）」占位
            stop_dist0, notional0, lev0 = direct_calc(x, tier)
            if notional0 is None:
                sig_cards.append(card(x['grade'], sym, x.get('env', ''), live, score,
                                      anchor_s, f"{x['stop']:.2f}", dead_s(x), f"{stop_dist0*100:.1f}",
                                      tier, '—', '—', zone_s(x), ('信号日', x['day']),
                                      f"⛔止损距离过宽({stop_dist0:.1%})，放弃该信号（同日候选缺失·按信号字段直算）" + _sup,
                                      tag_d, stop_eff=se, red_tag=rt, fuse=fuse_px(x), badge=zone_badge(x, lc), agetag=age_tag(x), sig_note=x.get('note', '')))
                continue
            sig_cards.append(card(x['grade'], sym, x.get('env', ''), live, score,
                                  anchor_s, f"{x['stop']:.2f}", dead_s(x), f"{stop_dist0*100:.1f}",
                                  tier, f"{notional0:g}", f"{lev0:g}", zone_s(x), ('信号日', x['day']),
                                  advice_of(x, None) + '（同日候选缺失·按信号字段直算）' + _sup,
                                  tag_d, stop_eff=se, red_tag=rt, fuse=fuse_px(x), badge=zone_badge(x, lc), agetag=age_tag(x), sig_note=x.get('note', '')))
            continue
        stop_dist = max(STOP_NEAR, (cd['anchor'] - cd['stop']) / cd['anchor'])
        notional, lev, sz_reason = pos_size(tier, stop_dist, _is_sun(x['day']))   # v1.7.39: HTML卡与账本机同源（pos_size 单源，含止损>MAX_STOP 放弃）
        if sz_reason:
            sig_cards.append(card(x['grade'], sym, x.get('env', ''), live, score,
                                  anchor_s, f"{cd['stop']:.2f}", dead_s(x), f"{stop_dist*100:.1f}",
                                  tier, '—', '—', zone_s(x), ('信号日', x['day']),
                                  f"⛔止损距离过宽({stop_dist:.1%})，放弃该信号" + _sup, tag_d, stop_eff=se, red_tag=rt, fuse=fuse_px(x), badge=zone_badge(x, lc), agetag=age_tag(x),
                                  sig_note=x.get('note', '')))    # v1.7.23: E4 企稳备注独立成行
            continue
        _cross = ''
        if sym in open_map:    # v1.7.17: 同标已有模拟仓——占位事实交叉标注
            _cross = f"｜该标的已有模拟仓（{open_map[sym]}开），本信号仅在册展示，按同标不重叠不入账"
        sig_cards.append(card(x['grade'], sym, x.get('env', ''), live, score,
                              anchor_s, f"{cd['stop']:.2f}", dead_s(x), f"{stop_dist*100:.1f}",
                              tier, ('—' if x.get('brk_expire') else f"{notional:g}"), ('—' if x.get('brk_expire') else f"{lev:g}"), zone_s(x), ('信号日', x['day']),
                              advice_of(x, cd) + _cross + _sup, tag_d, stop_eff=se, red_tag=rt, fuse=fuse_px(x), badge=zone_badge(x, lc), agetag=age_tag(x),
                              sig_note=x.get('note', '')))    # v1.7.23: E4 note 自内联拼接送入 sig_note 独立成行（原 advice+esc(note) 内联拼接）

    sig_by_sym = {sym: x for _, sym, x, _, _, _, _ in rows}
    sim_cards = []
    for p in sorted(open_pos, key=lambda q: -q['score']):
        x = sig_by_sym.get(p['sym'])
        g = x['grade'] if x else '·'
        env = x.get('env', '') if x else ''
        zone = zone_s(x) if x else '—'
        dead = dead_s(x) if x else '—'
        sd = f"{abs((p['stop']/p['anchor']-1))*100:.1f}" if p['anchor'] else '—'
        # v1.7.17: 旧仓卡只描述仓位自身状态，不引用任何其他信号的建议
        _age = p.get('age')
        _age_s = f" · 持仓 {_age}/{HARD_CAP} 天" + (" ⏳硬顶将至" if isinstance(_age, int) and _age >= HARD_CAP - 3 else "") if isinstance(_age, int) else ""
        note = f"模拟口径管理中：{p['day']} 开{_age_s} · 现浮 {p['live_ret']:+.1f}% · 止损 {p['stop']:.2f}"
        sk = skip_map.get(p['sym'])
        if sk:
            note += f"｜同标新触轨 {sk['n']} 次（最近 {sk['last'][5:]}）已按同标不重叠跳过"   # v1.7.42: 「有牌N次」子句随分级废除删除
        se_s = f"{x['stop_eff']:.2f}" if x and isinstance(x.get('stop_eff'), (int, float)) else '—'
        rt_s = '🚫周日·降权0.5·复评中' if x and x.get('sun_half') else ''
        sim_cards.append(card(g, p['sym'], env, p['live_ret'], p['score'],
                              f"{p['anchor']:.2f}", f"{p['stop']:.2f}", dead, sd,
                              p['tier'], f"{p['notional']:g}", f"{p['lev']:g}", zone,
                              ('开仓日', p['day']), note, (tag_of(x) if x else '—'), stop_eff=se_s, red_tag=rt_s,
                              sig_note=(x.get('note', '') if x else '')))    # v1.7.23: E4 模拟仓卡从简传 note（x 缺失时空）

    sample_note = '' if st['n_closed'] >= 100 else '（样本不足，&lt;100笔不构成有效性证据）'
    banner = f'''<div style="background:#2a0a0a;border:2px solid #ff3b30;border-radius:8px;padding:10px 14px;margin:0 0 8px 0;color:#ff453a;font-weight:700;font-size:14px;line-height:1.6">系统性质：右偏型趋势跟随系统——信号出现 → 进场 → 按趋势持有，严格按纪律出场离场。约 46% 的交易会被止损打掉（平均 −7.66%），这是必然的数学结果，不是系统坏了；利润全部来自拿得住的右尾（30 天硬顶均值 +32% · 趋势终结 +11%）。不敢扛浮亏、不敢拿单、手动干预止损，就不该用这套系统。月月盈利、回撤浅、胜率高——这个标准在任何真实交易系统上都不可达（顶级 CTA 同样有深回撤，趋势策略胜率普遍不到 45%），稳定的印钞机这个标准更是不存在。</div><div class="banner"><b>丁导K线交易系统</b><br>
自研引擎 v{st["ver"]} · {esc(st["up_ts"])} 北京时间更新（每天 00:35/04:35/08:35/12:35/16:35/20:35 点更新，此时间变了=发版正常）<br>
{esc(st["market_banner"])} ｜ 扫描 {st["pool_n"]} 标的 · 在册 {st["hit_n"]} · ⚠️ {st["warn"]}<br>
规则全历史战绩（诚实口径，含旧规则候选与硬顶退出）：{st["hist_n"]} 笔 · 胜率 {st["hist_win"]:.0f}% · 均值 {st["hist_avg"]:+.2f}% · 中位 {st["hist_med"]:+.2f}% ｜ 在册卡溢价为幸存者快照仅供参考<br>
扛单口径回测（2025-04→今 · 5171信号 · 含资金费 · 幸存者0.7折并列）：追卡片现价短线无超额（+5日超额 −0.27%）；回踩锚位进场+扛到 到站/趋势终结/30天硬顶 均值 +4.05%（0.7折 +2.83%，验证期衰减至 +2.44%）——历史回测≠未来承诺，非投资建议<br>
模拟仓: 在仓 {st["n_open"]} / 已平 {st["n_closed"]} ｜ 已平 {st["n_closed"]} 笔 · 胜率 {(st["win"]/st["n_closed"] if st["n_closed"] else 0):.0%} · 单笔均值 {st["avg"]:+.3f}% · 累计 {st["cum"]:+.2f}%（含资金费）{sample_note}<br>
页面读法：⚠️置顶先处理（破位观察·风控优先）→ 推荐口径=通过全部禁入门槛的信号全集（单档6%；评分含周一桶×1.3，标签≠推荐强度）→ 现价贴信号区=入场区、超锚太多=追高 → ✅到站默认走 → 🏁亮了挪仓 → 禁入沉底勿捡 ｜ 约束：并发≤8 · 单票≤10% · 总敞口≤50% · 杠杆≤5× · 止损距离>8%放弃 · 同日≤3只 · 孤星日禁入 · 周六信号不入册（行业分散暂缓·待行业数据源）<br>
券商挂单: 只挂保险丝单=锚×0.8（盘中防崩，不参与常规止损） | 止损只看收盘: 收盘&lt;收盘止损线→次日开盘无条件出, 死区内（收盘止损线~止损）照常持有（每日04:40判定）<br>
📌 每标的仅显示日期最新的一条信号；被顶掉信号的历史持仓收益已计入模拟账本</div>'''

    sim_html = chr(10).join(sim_cards)
    sig_html = chr(10).join(sig_cards + jin_cards)   # 禁入卡沉底
    obs_html = f'<p class="note">{esc(st.get("obs", ""))}</p>' if st.get('obs') else ''    # v1.7.39: 观察期监控指标行（页脚，空则略去）
    shadow_html = f'<p class="note">{esc(st.get("shadow", ""))}</p>' if st.get('shadow') else ''    # v1.7.23: E6 影子观察行（页脚免责上一行，空则略去）
    _ex = st.get('recent_exits') or []    # v1.7.33: 📋 近日出清面板（纯展示）
    if _ex:
        from collections import Counter as _C
        _cnt = _C(x['reason'] for x in _ex)
        _ex_rows = "".join(
            f'<div style="display:flex;gap:8px;font-size:13px;line-height:1.9">'
            f'<span style="width:18px">{REASON_EMO.get(x["reason"], "·")}</span>'
            f'<b style="min-width:96px">{esc(x["sym"])}</b>'
            f'<span style="color:#7c869c;width:44px">{esc(x["date"][5:])}</span>'
            f'<span style="width:72px">{REASON_SHORT.get(x["reason"], esc(x["reason"]))}</span>'
            f'<span class="{REASON_CLS.get(x["reason"], "")}" style="margin-left:auto;font-weight:700">{x["ret"]:+.1f}%</span></div>'
            for x in _ex[:40])
        _ex_tail = f'<div style="color:#7c869c;font-size:12px;margin-top:6px">仅显示最近 40 笔</div>' if len(_ex) > 40 else ''
        exits_html = (f'<h2>📋 近日出清（近7个交易日·共 {len(_ex)} 笔）</h2><div class="card">{_ex_rows}{_ex_tail}</div>')
    else:
        exits_html = '<h2>📋 近日出清</h2><div class="card" style="color:#7c869c">近 7 个交易日无出清</div>'
    return f'''<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>丁导K线交易系统</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#0e1117;color:#dbe2ee;
font:15px/1.5 -apple-system,'PingFang SC','Microsoft YaHei',sans-serif;padding:14px}}
.wrap{{max-width:640px;margin:0 auto}}
.banner{{background:#171c26;border:1px solid #232a38;border-radius:12px;padding:14px 16px;
margin-bottom:14px;font-size:13px;color:#7c869c;line-height:1.9}}
.banner b{{color:#dbe2ee;font-size:17px}}
h2{{font-size:16px;margin:20px 0 10px}}
.grid2{{display:grid;grid-template-columns:1fr;gap:14px}}
.card{{background:#171c26;border:1px solid #232a38;border-radius:12px;padding:14px 16px}}
.card-h{{display:flex;align-items:center;gap:8px;margin-bottom:10px;flex-wrap:wrap}}
.tag{{font-size:14px;font-weight:700;border:1px solid #2b3446;border-radius:6px;padding:1px 6px}}.card-h b{{font-size:18px}}
.score{{margin-left:auto;color:#f5c542;font-size:14px;font-weight:700}}
.live{{font-size:16px;font-weight:800}}
.env{{font-size:13px;font-weight:600}}
.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px 10px}}
.grid i{{display:block;font-style:normal;color:#7c869c;font-size:12px}}
.grid em{{font-style:normal;font-weight:700;font-size:15px}}
.grn{{color:#2ecc71}}.red{{color:#e74c3c}}.sm{{font-size:13px}}
.note{{margin-top:10px;color:#7c869c;font-size:13px;border-top:1px dashed #232a38;padding-top:8px}}
</style></head><body><div class="wrap">
{banner}
<h2>💼 模拟账户（在仓 {st["n_open"]}）</h2><div class="grid2">{sim_html}</div>
<h2>📋 在册信号（{len(sig_cards)}）</h2><div class="grid2">{sig_html}</div>
{shadow_html}
{exits_html}
{obs_html}
<p class="note">⚠️ 以上为历史统计规则输出，非投资建议；仓位与杠杆自定，极端行情下任何止损价都可能被跳空击穿。模拟成交假设 T+1 开盘价、无滑点与流动性约束；展示口径与模拟口径不同，模拟仓更保守。</p>
</div></body></html>'''

def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    print(f"[replica] 包代码版本 v{__version__}")
    tok = os.environ.get("KX_GH_TOKEN", "")
    cli = KxClient(signal_age_days=16, timeout=30, retries=3, retry_delay=2.0)
    items = cli.get_signals('futures', '1d', 1, 500).get('items') or []
    names = {it['symbol']: (it.get('name') or '') for it in items
             if (it.get('underlying_type') or '') == 'EQUITY' and it.get('symbol')}
    pool = sorted(names)
    now_day = datetime.now(timezone.utc).strftime('%Y-%m-%d')   # v1.7.36: 前置——analyse 需据此识别末根forming bar

    def one(sym):
        try:
            d = cli.get_kline(sym, 'futures', '1d', BARS)
            sig, cands, tdays, lc, dset, sig_by_day = analyse(sym, d.get('bars') or [], now_day)
            return sym, sig, cands, tdays, lc, dset, sig_by_day
        except Exception:
            return sym, 'ERR', [], set(), 0, set(), {}

    with ThreadPoolExecutor(WORKERS) as ex:
        results = list(ex.map(one, pool))

    day_trig = Counter()
    sym_cands, sigs, closes, sig_by_days = {}, {}, {}, {}   # v1.7.30: +sig_by_days 展示层状态索引（sym→{day: sig}）
    calendar = set()
    for sym, sig, cands, tdays, lc, dset, sig_by_day in results:
        if sig == 'ERR': continue
        sigs[sym] = sig
        sym_cands[sym] = cands
        closes[sym] = lc
        sig_by_days[sym] = sig_by_day   # v1.7.30
        calendar |= dset
        for d in tdays: day_trig[d] += 1
    cal = sorted(calendar)
    pool_n = max(1, len(pool))

    def layer_prev(dstr):
        """T-1 自然交易日触发数→层（日历化，零触发日=孤星；归一化：孤星<1.5%池，批量>8%池）。"""
        import bisect
        k = bisect.bisect_left(cal, dstr)
        if k <= 0: return '常规'
        cnt = day_trig.get(cal[k-1], 0)
        if cnt < 0.015*pool_n: return '孤星'
        if cnt > 0.08*pool_n: return '批量'
        return '常规'

    def lay_of_latest():
        """今日市况 = 最近一个已收盘交易日的 T-1。"""
        import bisect
        k = bisect.bisect_left(cal, now_day)
        if k == 0: return '常规'
        ref = cal[k-1] if (k < len(cal) and cal[k] == now_day) else cal[-1]
        k2 = cal.index(ref)
        if k2 <= 0: return '常规'
        cnt = day_trig.get(cal[k2-1], 0)
        if cnt < 0.015*pool_n: return '孤星'
        if cnt > 0.08*pool_n: return '批量'
        return '常规'

    # ---- 组合级模拟（时间序 sweep + 熔断 + 行业分散）----
    # 持仓自开仓日起占用名义额度，直到 exit_date（含）后下一候选日起释放——
    # 保证总敞口/行业敞口在持仓重叠期真实生效（技术评审 #1 修复）。
    active, closed = [], []
    skip_n = Counter()
    skip_detail = {}    # v1.7.17: sym -> [(day, grade), ...] 同标不重叠跳过明细
    day_new = Counter()
    cands_all = []
    for sym, cands in sym_cands.items():
        for cd in cands:
            cd['sym'] = sym
            cd['sector'] = sector_of(names.get(sym, ''))
            cands_all.append(cd)
    cands_all.sort(key=lambda x: (x['day'], x['sym'], 1 if x.get('src') == 'G' else 0))   # 决胜键: 同日同标普通信号优先于G

    def sweep(day):
        """回收 exit_date<=day 的在仓仓位（当日收盘已平，次日额度释放）。"""
        for p in active[:]:
            if p['exit_date'] and p['exit_date'] <= day:
                active.remove(p)    # v1.7.21: 删 sector_state 死代码（仅递减从未递增，行业限额实际用实时 sum(active)，此缓存从未生效且键缺失会 KeyError）

    for cd in cands_all:
        sweep(cd['day'])
        sym = cd['sym']
        if any(p['sym'] == sym for p in active):
            skip_n['已有持仓'] += 1
            skip_detail.setdefault(sym, []).append((cd['day'], cd['grade']))    # v1.7.17: 跳过事实可见化
            continue
        lay = layer_prev(cd['day'])
        tier = tier_of(cd['grade'], lay, cd['env'])
        if tier == '禁入':
            skip_n['禁入'] += 1; continue
        notional, lev, sz_reason = pos_size(tier, cd['stop_dist'], _is_sun(cd['day']))   # v1.7.39: 仓位/杠杆单源——单票≤CAP_TICKER、杠杆≤MAX_LEV、止损距离>MAX_STOP 在此放弃
        if sz_reason:
            skip_n[sz_reason] += 1; continue
        reason = portfolio_admit(active, sym, notional, day_new[cd['day']])   # v1.7.39: 中间态准入真执行——并发≤CAP_CONCURRENCY/总敞口≤CAP_GROSS/同日≤CAP_DAY_NEW
        if reason:
            skip_n[reason] += 1; continue
        # TODO(行业分散·暂缓): 原行业限额块（CAP_SECTOR/CAP_SECTOR_N/CAP_SECTOR_DAY）v1.7.39 停用——无行业数据源，接入后恢复（见常量区 TODO）
        b = cd.get('sector', '宽基')
        pos = {'sym': sym, 'day': cd['day'], 'anchor': cd['anchor'], 'tier': tier,
               'notional': notional, 'lev': lev, 'stop': cd['stop'], 'sector': b, 'age': cd['n'] - 1 - cd['idx'],   # v1.7.22(i): cd['n']=该标的K线总数
               'score': score_of(cd['grade'], lay, cd['env'], cd['day']),
               'exit_date': cd.get('exit_date'), 'exit_px': cd.get('exit_px'),
               'exit_idx': cd.get('exit_day'),
               'reason': cd.get('reason'), 'ret': cd.get('ret'),
               'open_idx': cd['idx'], 'n': cd['n']}
        active.append(pos)
        day_new[cd['day']] += 1
        # v1.7.39: 行业同日新开计数随行业限额块一并停用（TODO 见常量区）
        # 平仓结算：推演已定退出日的，按当时价格入账（占用已由 sweep 释放）
        if pos['exit_date'] is not None:
            days_held = max(1, (pos['exit_idx'] or pos['open_idx']) - pos['open_idx'])
            pos['pnl'] = (pos['ret'] or 0)*notional/100 - notional*FUND_FEE_DAY*days_held
            pos['days_held'] = days_held
            closed.append(pos)
            # v1.7.21(🟠2): 不立即移出 active——由 sweep 在 exit_date 到期时释放，
            # 保持同标不重叠占位与 sector 占用直到真实退出日（修复持有期内新候选绕过 skip）
    # 数据末端仍未退出的 = 真在仓
    open_pos = [p for p in active if p['exit_date'] is None]
    for p in open_pos:
        lc = closes.get(p['sym'], 0)
        p['live_ret'] = (lc/p['anchor']-1)*100 if lc and p['anchor'] else 0.0

    realized = [p['pnl'] for p in closed]
    win = sum(1 for x in realized if x > 0)
    cum = sum(realized)

    # ---- v1.7.39: 60 交易日观察期监控指标（页脚输出）——条款：单日DD>20%→次日降杠杆50% / PF<1.0→停机 / 期满 PF≥1.3→转正 ----
    def obs_metrics():
        """单日DD=按 exit_date 聚合已平盈亏的逐日净值单日最大跌幅；PF=总盈利/总亏损（已平，含资金费）；
        观察交易日数=首仓开仓日→now_day 的日历交易日跨度（封顶 60 显示）。"""
        day_pnl = {}
        for p in closed:
            _d = p.get('exit_date')
            if _d: day_pnl[_d] = day_pnl.get(_d, 0.0) + p['pnl']
        prev_eq, max_dd = 100.0, 0.0
        for _d in sorted(day_pnl):
            eq = prev_eq + day_pnl[_d]
            if prev_eq > 0: max_dd = max(max_dd, max(0.0, (prev_eq - eq) / prev_eq))
            prev_eq = eq
        _gw = sum(x for x in realized if x > 0)
        _gl = -sum(x for x in realized if x < 0)
        pf = (_gw / _gl) if _gl > 1e-12 else None
        _first = min((p['day'] for p in closed + open_pos), default=None)
        n_obs = (len([d for d in cal if _first <= d <= now_day]) - 1) if (_first and cal) else 0
        return max(0, n_obs), max_dd, pf
    obs_days, obs_dd, obs_pf = obs_metrics()
    _pf_s = '—' if obs_pf is None else ('∞' if obs_pf > 100 else f"{obs_pf:.2f}")
    obs_line = (f"观察期监控（60交易日条款·中间态单档）: 交易日 {min(obs_days, 60)}/60 | "
                f"单日最大DD {obs_dd:.1%}（>20%→次日降杠杆50%）| PF {_pf_s}（<1.0→停机；期满≥1.3→转正）")

    # ---- 全历史战绩（诚实口径：全部候选含已平，v1.7.22 横幅主口径）----
    _all_rets = np.array([c['ret'] for cs in sym_cands.values() for c in cs if c.get('ret') is not None]) / 100.0
    hist_n = int(len(_all_rets))
    hist_win = float((_all_rets > 0).mean() * 100) if hist_n else 0.0
    hist_avg = float(_all_rets.mean() * 100) if hist_n else 0.0
    hist_med = float(np.median(_all_rets) * 100) if hist_n else 0.0

    # ---- v1.7.23: E6 影子观察统计（标签≠推荐强度）——只用 ret 非 None 的已平候选，n=0 的桶略去 ----
    def _shadow_stats():
        buckets = {'周一干净桶': [], 'G路径': []}
        for cs in sym_cands.values():
            for c in cs:
                if c.get('ret') is None:
                    continue
                if c.get('mon_clean'):
                    buckets['周一干净桶'].append(c['ret'])
                if c.get('src') == 'G':
                    buckets['G路径'].append(c['ret'])
        parts = []
        for _name, _rets in buckets.items():
            if not _rets:
                continue
            _arr = np.array(_rets)
            parts.append(f"{_name} n={len(_arr)} 胜率{(_arr > 0).mean()*100:.0f}% 均值{_arr.mean():+.2f}%")
        return ("影子观察（标签≠推荐强度）: " + " ｜ ".join(parts)) if parts else ""
    shadow_line = _shadow_stats()

    # ---- 展示 ----
    hit = {s: v for s, v in sigs.items() if v}
    warn = sum(1 for v in hit.values() if v['warn'])
    rank = {'⚠️': 0, '🥇': 1, '🥈': 2, '🥉': 3, '·': 9}
    rows = []
    for sym in sorted(hit):
        x = hit[sym]
        # v1.7.31(b): 「·」级无警示卡暂不在此过滤——若顶替了存活旧卡（血缘段判 held_old）则沉底保留
        #（用户拍板方案A，ORCL 案例：旧卡 10-09 活卡被 · 级新卡顶替+新卡被过滤=整页消失）；无存活旧卡的仍隐藏（下方剔除）。
        cands = sym_cands.get(sym) or []
        cd = next((cc for cc in cands if cc['day'] == x['day']), None)
        lay = layer_prev(x['day'])
        tier = tier_of(x['grade'], lay, x['env'])
        score = score_of(x['grade'], lay, x['env'], x['day'], mon_clean=x.get('mon_clean', False))    # v1.7.23: E1 传周一干净桶旗标
        rows.append((rank.get('⚠️' if x['warn'] else x['grade'], 9), sym, x, cd, lay, tier, score))
    # v1.7.31(a): 期满红旗升权（用户拍板 2026-10-14「提升期满的权重新信号给他让路带一天」）——
    # 被新信号顶替的 brk_expire 卡同屏展示一天（归🏁出清组沉底，不占⚠️位）；
    # 期满次日引擎 lag≥4 自动出清，恢复正常「每标的仅最新一条」顶替。纯展示层。
    for sym, sbd in sig_by_days.items():
        x_cur = hit.get(sym)
        for _d, _x in sbd.items():
            if _x.get('brk_expire') and not (x_cur and x_cur.get('day') == _d):
                _cands = sym_cands.get(sym) or []
                _cd = next((cc for cc in _cands if cc['day'] == _d), None)
                _lay = layer_prev(_d)
                rows.append((rank.get(_x['grade'], 9), sym, _x, _cd, _lay,
                             tier_of(_x['grade'], _lay, _x.get('env', '')),
                             score_of(_x['grade'], _lay, _x.get('env', ''), _x['day'], mon_clean=_x.get('mon_clean', False))))
    rows.sort(key=lambda r: row_sort_key(r, closes))    # v1.7.23: E2 多键排序锁死（⚠️置顶→状态分组→评分→盈亏比→新鲜度→字母序）
    # v1.7.29(b): 顶替明示——展示信号顶替同标旧候选时附旧卡纪律位摘要（用户 10-14 指出跟单视图纪律位丢失）
    # 大师团 5 票裁定：旧卡血缘必须结构化可读（锚/止损/状态/浮盈%/距到站%），旧卡在仓时新卡语义降级+非加仓防火墙
    # v1.7.30: 状态读取源改 sig 展示层（候选环 exit_date 9/9 全 None=坏源，工程取证）；四态收敛矩阵+中性安全网（研究主管终裁，用户拍板）：
    #   live→持有中·浮盈%·距到站%｜⚠️观察中→⚠️破位观察中·浮盈%（无距到站）｜⛔brk_expire/killed→⛔真破位·已离场·双「—」｜✅dead/flag→✅行程已走完·已平·双「—」｜不可判定→中性（不渲染状态字段，绝不回退「持有中」）
    for _r in rows:
        _sym, _x = _r[1], _r[2]
        _olds = sorted([cc for cc in (sym_cands.get(_sym) or []) if cc['day'] < _x['day']], key=lambda c: c['day'])
        if _olds:
            _o = _olds[-1]
            _lc = closes.get(_sym, 0)
            _o_anchor = _o.get('anchor') or 0
            _o_stop = _o.get('stop', 0)
            _sig0 = (sig_by_days.get(_sym) or {}).get(_o['day'])   # 旧卡展示层状态（与卡面同源，含出清卡）
            if _o.get('exit_date'):
                # 账本已平（现状保留，原样不动——终裁规格第①条）
                _o_state = '已平·' + (_o.get('reason') or '') + (f" {_o['ret']:+.1f}%" if _o.get('ret') is not None else '')
            elif _sig0 is None:
                _o_state = ''   # v1.7.30 安全网：状态不可判定→中性渲染，绝不标「持有中」
            elif _sig0.get('brk_expire') or _sig0.get('killed'):
                _o_state = '⛔真破位·已离场（模拟仓口径）·浮盈—·距到站—'
            elif '观察中' in (_sig0.get('warn') or ''):   # v1.7.30: warn 格式=「⚠️破位MM-DD观察中」（带日期），以「观察中」判定（子串匹配修复）
                _pl = f"·浮盈{(_lc/_o_anchor-1)*100:+.1f}%" if _lc and _o_anchor else ''
                _o_state = f"⚠️破位观察中{_pl}"   # 观察期约束=止损/期满，展示距到站=虚假希望（终裁：无距到站）
            elif _sig0.get('dead') or _sig0.get('flag'):
                _o_state = '✅行程已走完·已平·浮盈—·距到站—'
            else:
                _pl = f"浮盈{(_lc/_o_anchor-1)*100:+.1f}%" if _lc and _o_anchor else ''
                _dp = _o.get('dead_px')
                _dz = f"·距到站{(_dp/_lc-1)*100:+.1f}%" if _dp and _lc else ''
                _o_state = '持有中' + (f"·{_pl}" if _pl else '') + _dz
                _x['held_old'] = True   # 旧卡在仓 → 用户可能仍持有，新卡动词降级为在册监控（德鲁肯米勒裁决：旧仓存活期禁出加仓暗示）
            _of = f"{_o_anchor*0.8:.2f}" if _o_anchor < 1000 else f"{_o_anchor*0.8:.1f}"   # v1.7.31: 位数随锚（审计🟡）
            _x['supersede'] = (f"顶替 {_o['day'][5:]} 旧卡：锚{_o_anchor:.2f}/止损{_o_stop:.2f}/保险丝{_of}"
                               + (f"·{_o_state}" if _o_state else '')
                               + "｜展示位替换≠加仓指令，旧仓按原纪律管理")
    # v1.7.42: 原「·级无警示卡剔除规则」（v1.7.31b）随🥈分级废除停用（agent-7f2a447d）——
    # 推荐口径改为「通过全部禁入门槛的信号全集」，全信号 ·级，若保留剔除则整页清空；
    # 禁入兜底由 tier_of 孤星门槛+沉底展示承接，⚠️/血缘/卡龄通道不受影响。
    rows.sort(key=lambda r: row_sort_key(r, closes))    # v1.7.31(b): 重排（血缘 supersede/held_old 已就位）

    tz8 = timezone(timedelta(hours=8))
    up_ts = datetime.now(tz8).strftime('%Y-%m-%d %H:%M')
    today_lay = lay_of_latest()
    banner = {'孤星': '⛔ 今日孤星市况·不适合抄底，仅观察，勿开新仓',
              '批量': '🟢 今日批量出清市况·β修复窗口，优选评分最高者',
              '常规': '市况：常规日，按评分与档位正常筛选'}[today_lay]

    lines = [f"【K线复刻监控 · 自研引擎 v{__version__}】{now_day} (UTC)",
             f"{RED_TXT}",
             f"⏱️ 本次更新: {up_ts} 北京时间（每天 00:35/04:35/08:35/12:35/16:35/20:35 点更新，此时间变了=发版正常）",
             banner,
             f"扫描 {len(pool)} 标的 | 在册 {len(hit)} | ⚠️ {warn} | 模拟仓: 在仓 {len(open_pos)} / 已平 {len(closed)}",
             f"规则全历史战绩（诚实口径）: {hist_n} 笔 | 胜率 {hist_win:.0f}% | 均值 {hist_avg:+.2f}% | 中位 {hist_med:+.2f}%（在册卡溢价为幸存者快照）",
             f"扛单口径回测: 追现价短线无超额(+5日 -0.27%) | 回踩锚位进场+扛单(到站/趋势终结/30天硬顶) 均值 +4.05% (0.7折 +2.83%, 验证期 +2.44%, 含资金费) (2025-04→今 5171信号, 历史回测≠未来承诺)",
             "页面读法：⚠️置顶先处理（破位观察·风控优先）→ 推荐口径=通过全部禁入门槛的信号全集（单档6%；评分含周一桶×1.3，标签≠推荐强度）→ 现价贴信号区=入场区、超锚太多=追高 → ✅到站默认走 → 🏁亮了挪仓 → 禁入沉底勿捡",    # v1.7.42: 主信号唯一分级口径废除（agent-7f2a447d）
             "券商挂单: 只挂保险丝单=锚×0.8(盘中防崩, 不参与常规止损) | 止损只看收盘: 收盘<收盘止损线→次日开盘无条件出, 死区内(收盘止损线~止损)照常持有(每日04:40判定)",    # v1.7.31: 交易分析团队终裁挂单转换规则
             "约束：并发≤8 | 单票≤10% | 总敞口≤50% | 杠杆≤5× | 止损距离>8%放弃 | 同日≤3只 | 孤星日禁入 | 周六信号不入册（行业分散暂缓·待行业数据源）",
             "📌 每标的仅显示日期最新的一条信号；被顶掉信号的历史持仓收益已计入下方模拟账本",
             "=" * 46]
    if shadow_line:    # v1.7.23: E6 影子观察统计行插在「约束：」行之后
        _ci = next(i for i, l in enumerate(lines) if l.startswith('约束：'))
        lines.insert(_ci + 1, shadow_line)
    if closed:
        sample_note = '' if len(closed) >= 100 else '（样本不足，<100笔不构成有效性证据）'
        lines.append(f"💼 模拟账户（规则化全量模拟，无幸存者偏差）: 已平 {len(closed)} 笔 | "
                     f"胜率 {win/len(closed):.0%} | 单笔均值 {np.mean(realized):+.3f}% | 累计 {cum:+.2f}%（含资金费）{sample_note}")
    else:
        lines.append("💼 模拟账户：暂无已平仓位（合格信号出现后自动开仓跟踪）")
    for p in sorted(open_pos, key=lambda x: -x['score']):
        lines.append(f"  ▶ 在仓 {p['sym']} {p['tier']} {p['notional']}% {p['lev']}x 锚{p['anchor']:.2f} "
                     f"止损{p['stop']:.2f} 开仓{p['day'][5:]} 现浮 {p['live_ret']:+.1f}%")
    lines.append("=" * 46)
    for _, sym, x, cd, lay, tier, score in rows:
        price_s = f"{x['anchor']:.2f}" if x['anchor'] < 1000 else f"{x['anchor']:.1f}"
        _verb = '在册监控' if x.get('held_old') else '买入'   # v1.7.29: 旧卡在仓时新卡动词降级（德鲁肯米勒：旧仓存活期禁出加仓暗示）
        _sup = f"｜{x['supersede']}" if x.get('supersede') else ''   # v1.7.29: 顶替血缘（旧卡日/锚/止损/状态/浮盈%/距到站%+非加仓防火墙）
        _lc = closes.get(sym, 0)
        _zb = zone_badge(x, _lc)
        lines.append(f"{('🚫周日·降权0.5·复评中 ' if x.get('sun_half') else '')}{(brk_red_tag(x) + ' ' if x.get('brk_expire') else '')}{('⚠️' if x['warn'] else tag_of(x))} {(age_tag(x) + ' ') if age_tag(x) else ''}{sym} {_verb} {x['day']} 锚{price_s} "
                     f"支撑阻力区{x['zone']} 收盘止损线{x.get('stop_eff', '—')}{_zb} 保险丝{fuse_px(x)}(锚×0.8) CCI{x['cci']:.0f}{x['warn']}{x.get('note', '')}{x.get('haos', '')}"
                     f"{x.get('dead', '')}{x.get('flag', '')}{_sup}")
        if tier == '禁入':
            # v1.7.29: P0 止血——禁入是附加状态不是替换状态：advice 只追加不覆盖（TEM 案例：破位观察期止损位被孤星禁入标注整块吞掉）
            lines.append(f"   └ 评分{score} {lay}日 禁入（{x['grade']}|{lay} 不满足开仓条件）｜{state_advice(x, cd)}")
            continue
        if cd is None:
            # v1.7.23: E3 同日候选缺失——按信号字段直算仓位（展示层，裁决 A），输出与常规卡同格式
            stop_dist0, notional0, lev0 = direct_calc(x, tier)
            if notional0 is None:
                lines.append(f"   └ 评分{score} {lay}日 ⛔止损距离过宽({stop_dist0:.1%})，放弃该信号（同日候选缺失·按信号字段直算）")
                continue
            advice0 = state_advice(x)   # v1.7.29: 公共提取，禁入/直算/常规三 branch 文案零漂移
            _n0, _l0 = ('—', '—') if x.get('brk_expire') else (f"{notional0}%", f"{lev0}x")   # v1.7.25 审计🟢: 同上
            lines.append(f"   └ 评分{score} {lay}日 {tier} {_n0} {_l0} | "
                         f"止损{x['stop']:.2f}(收盘确认,距锚{stop_dist0:.1%}) | {advice0}（同日候选缺失·按信号字段直算）")
            continue
        stop_dist = max(STOP_NEAR, (cd['anchor']-cd['stop'])/cd['anchor'])
        notional, lev, sz_reason = pos_size(tier, stop_dist, _is_sun(x['day']))   # v1.7.39: 展示层与账本机同源（pos_size 单源，含止损>MAX_STOP 放弃）
        if sz_reason:
            lines.append(f"   └ 评分{score} {lay}日 ⛔止损距离过宽({stop_dist:.1%})，放弃该信号")
            continue
        advice = state_advice(x, cd)   # v1.7.29: 公共提取（v1.7.25 期满事实陈述/模拟仓离场后缀语义与原内联逐字一致）
        _n_s, _l_s = ('—', '—') if x.get('brk_expire') else (f"{notional}%", f"{lev}x")   # v1.7.25 审计🟢: 期满卡仓位杠杆置—（已出清无可交易建议）
        lines.append(f"   └ 评分{score} {lay}日 {tier} {_n_s} {_l_s} | "
                     f"止损{cd['stop']:.2f}(收盘确认,距锚{stop_dist:.1%}) | {advice}")
    if not rows:
        lines.append("（当前无在册信号）")
    _recent_exits = collect_recent_exits(sym_cands)   # v1.7.33: 📋 近日出清面板（纯展示，页面尾部；计算一次双通道复用）
    lines.extend(exits_panel_text(_recent_exits))
    lines.append(obs_line)    # v1.7.39: 60交易日观察期监控指标（页脚输出）
    lines.append(f"拦截统计: " + " ".join(f"{k}{v}" for k, v in skip_n.most_common()) if skip_n else "")
    text = "\n".join(lines) + "\n"
    text += ("\n⚠️ 以上为历史统计规则输出，非投资建议；仓位与杠杆自定，极端行情下任何止损价都可能被跳空击穿。\n"
             "⚠️ 模拟成交假设 T+1 开盘价、无滑点与流动性约束；破位统一容忍口径（首破观察2天，收复信号区上沿=复活）；展示与模拟同口径(v1.7.14)。\n")
    print(f"[replica] {now_day} 状态页生成: {len(hit)} 标的 / {len(rows)} 推荐 / {len(text.encode())//1024}KB")

    # ---- v1.7.9 卡片版 view.html（渲染层，判定与文本页同源）----
    html_text = render_html(rows, closes, open_pos, {
        'ver': __version__, 'up_ts': up_ts, 'market_banner': banner,
        'pool_n': len(pool), 'hit_n': len(hit), 'warn': warn,
        'hist_n': hist_n, 'hist_win': hist_win, 'hist_avg': hist_avg, 'hist_med': hist_med,
        'n_open': len(open_pos), 'n_closed': len(closed),
        'shadow': shadow_line,    # v1.7.23: E6 影子观察统计行送 HTML 页脚
        'obs': obs_line,    # v1.7.39: 60交易日观察期监控指标送 HTML 页脚
        'recent_exits': _recent_exits,    # v1.7.33: 📋 近日出清面板数据（纯展示，复用文本页同一次计算）
        'win': win if closed else 0, 'avg': float(np.mean(realized)) if realized else 0.0,
        'cum': cum,
        'skip_by_sym': {k: {'n': len(v), 'last': max(d for d, _ in v),
                            'graded': sum(1 for _, g in v if g in ('🥇', '🥈'))}   # v1.7.42: 存量键名保留（🥈废除后恒0，仅兼容渲染字段）
                        for k, v in skip_detail.items()}})    # v1.7.17
    print(f"[replica] view.html 卡片版生成: {len(rows)} 信号卡 / {len(open_pos)} 模拟仓卡 / {len(html_text.encode())//1024}KB")

    if tok:
        hdr = {"Authorization": f"Bearer {tok}"}
        hhmm = datetime.now(tz8).strftime('%m%d-%H%M')
        for fname in (f"status/daily-{hhmm}.txt", "status/view.html", "status/latest.txt", "status/live.txt"):
            try:
                g = requests.get(f"{GH_API}/{fname}", headers=hdr, timeout=15)
                payload = html_text if fname == "status/view.html" else text
                data = {"message": f"replica status {now_day}", "content": base64.b64encode(payload.encode()).decode()}
                if g.status_code == 200 and g.json().get("sha"): data["sha"] = g.json()["sha"]
                p = requests.put(f"{GH_API}/{fname}", headers=hdr, json=data, timeout=30)
                print(f"[replica] 上传 {fname}: {'OK' if p.status_code in (200, 201) else f'HTTP {p.status_code}'}")
            except Exception as e:
                print(f"[replica] 上传 {fname} 异常: {e}")
        time.sleep(15)   # ★ 上传完等 GitHub 提交传播，再 purge 防竞态钉死旧缓存（评审 #10）
        # ---- 缓存交付：四通道统一 purge + 新鲜度自检（SRE 方案 A，2026-10-11）----
        # 根因：jsDelivr 对高频更新的固定文件名，purge 可能被节点钉住/限流；
        # 对策：不再依赖单通道，四通道全刷，并回读校验，哪个通道旧一目了然。
        mirrors = ('cdn.jsdelivr.net', 'fastly.jsdelivr.net',
                   'gcore.jsdelivr.net', 'testingcf.jsdelivr.net')
        # ⚠️ purge 按路径限流（实测 throttlingReset≈600s）：每轮每路径只请求一次，
        #    不做镜像预热 GET——多发只会打满配额让刷新彻底失效（2026-10-11 实测教训）
        for fname in ('status/live.txt', 'status/latest.txt', 'status/view.html'):
            try:
                p = requests.get(f"https://purge.jsdelivr.net/gh/Llng125256/kx-combo@main/{fname}", timeout=15)
                th = 'throttled' if 'throttled' in p.text else 'ok'
                print(f"[replica] purge {fname}: {th}")
            except Exception:
                pass
        expect = f"v{__version__}"
        state = {h: '旧' for h in mirrors}
        for attempt in range(3):        # purge 传播需要时间：三轮轮询，最长约 90 秒判定
            time.sleep(25)
            for host in mirrors:
                if state[host] == '新':
                    continue
                try:
                    r = requests.get(f"https://{host}/gh/Llng125256/kx-combo@main/status/live.txt", timeout=15)
                    state[host] = '新' if expect in r.text[:80] else ('旧' if r.status_code == 200 else '异常')
                except Exception:
                    state[host] = '超时'
            if all(v == '新' for v in state.values()):
                break
        print(f"[replica] 缓存校验: " + " ".join(f"{h.split('.')[0]}={v}" for h, v in state.items())
              + f"（目标版本 {expect}，旧=该通道 CDN 缓存未刷新，页面首行时间戳为准）")
        # 可选直达通道：设置 KX_WECHAT_WEBHOOK 即推精简版到企微，绕过 CDN 缓存
        wh = os.environ.get("KX_WECHAT_WEBHOOK", "")
        if wh:
            push_summary(lines, wh, f"daily-{hhmm}.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
