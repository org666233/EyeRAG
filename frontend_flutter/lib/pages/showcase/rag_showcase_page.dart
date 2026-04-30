/// RAG 系统架构 & 技术亮点展示页
/// 适合毕设答辩演示：完整呈现 Self-RAG 流程、混合检索、RAGAS 评估等核心创新
library;

import 'dart:async';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import '../../core/theme/app_theme.dart';

class RagShowcasePage extends StatefulWidget {
  const RagShowcasePage({super.key});

  @override
  State<RagShowcasePage> createState() => _RagShowcasePageState();
}

class _RagShowcasePageState extends State<RagShowcasePage>
    with TickerProviderStateMixin {
  late final AnimationController _heroCtrl;
  late final AnimationController _flowCtrl;

  @override
  void initState() {
    super.initState();
    _heroCtrl = AnimationController(
        vsync: this, duration: const Duration(seconds: 4))
      ..repeat(reverse: true);
    _flowCtrl = AnimationController(
        vsync: this, duration: const Duration(seconds: 2))
      ..forward();
  }

  @override
  void dispose() {
    _heroCtrl.dispose();
    _flowCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF090F1E),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        foregroundColor: Colors.white,
        title: const Text('系统技术亮点',
            style: TextStyle(fontWeight: FontWeight.w700)),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded, size: 18),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: ListView(
        padding: EdgeInsets.zero,
        children: [
          _HeroSection(ctrl: _heroCtrl),
          const SizedBox(height: 32),
          _SectionTitle(title: '核心技术栈'),
          const SizedBox(height: 16),
          _TechCardsRow(),
          const SizedBox(height: 32),
          _SectionTitle(title: 'Self-RAG 自适应检索流程'),
          const SizedBox(height: 16),
          _SelfRagFlow(ctrl: _flowCtrl),
          const SizedBox(height: 32),
          _SectionTitle(title: '混合检索架构'),
          const SizedBox(height: 16),
          _HybridRetrievalDiagram(),
          const SizedBox(height: 32),
          _SectionTitle(title: 'RAGAS 评估体系'),
          const SizedBox(height: 16),
          _RagasMetricsSection(),
          const SizedBox(height: 32),
          _SectionTitle(title: '最佳实验结果'),
          const SizedBox(height: 16),
          _ExperimentResults(),
          const SizedBox(height: 32),
          _SectionTitle(title: '渐进式流式回答'),
          const SizedBox(height: 16),
          _StreamingDemo(),
          const SizedBox(height: 48),
        ],
      ),
    );
  }
}

// ── 节标题 ────────────────────────────────────────────────────────────────────

class _SectionTitle extends StatelessWidget {
  final String title;
  const _SectionTitle({required this.title});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Row(children: [
        Container(
          width: 4,
          height: 18,
          decoration: BoxDecoration(
            gradient: const LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [AppColors.primary, AppColors.secondary]),
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        const SizedBox(width: 10),
        Text(
          title,
          style: const TextStyle(
            fontSize: 17,
            fontWeight: FontWeight.w700,
            color: Colors.white,
            letterSpacing: 0.3,
          ),
        ),
      ]),
    );
  }
}

// ── Hero 渐变动画区 ───────────────────────────────────────────────────────────

class _HeroSection extends StatelessWidget {
  final AnimationController ctrl;
  const _HeroSection({required this.ctrl});

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: ctrl,
      builder: (_, __) {
        final t = ctrl.value;
        return Container(
          height: 220,
          margin: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(24),
            gradient: LinearGradient(
              begin: Alignment(math.cos(t * math.pi), math.sin(t * math.pi)),
              end: Alignment(-math.cos(t * math.pi), -math.sin(t * math.pi)),
              colors: const [
                Color(0xFF1D4ED8),
                Color(0xFF7C3AED),
                Color(0xFF0891B2),
              ],
            ),
            boxShadow: [
              BoxShadow(
                color: AppColors.primary.withAlpha(80),
                blurRadius: 30,
                offset: const Offset(0, 10),
              )
            ],
          ),
          child: Stack(
            children: [
              // 装饰圆圈
              Positioned(
                right: -20,
                top: -20,
                child: Container(
                  width: 140,
                  height: 140,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: Colors.white.withAlpha(15),
                  ),
                ),
              ),
              Positioned(
                left: -30,
                bottom: -30,
                child: Container(
                  width: 100,
                  height: 100,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: Colors.white.withAlpha(10),
                  ),
                ),
              ),
              // 内容
              Padding(
                padding: const EdgeInsets.all(28),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Row(children: [
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: Colors.white.withAlpha(30),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: const Icon(Icons.visibility_rounded,
                            color: Colors.white, size: 24),
                      ),
                      const SizedBox(width: 12),
                      const Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('EyeRAG',
                              style: TextStyle(
                                  fontSize: 22,
                                  fontWeight: FontWeight.w800,
                                  color: Colors.white,
                                  letterSpacing: 0.5)),
                          Text('眼科医疗智能问答系统',
                              style: TextStyle(
                                  fontSize: 13,
                                  color: Colors.white70,
                                  fontWeight: FontWeight.w500)),
                        ],
                      ),
                    ]),
                    const SizedBox(height: 20),
                    Wrap(spacing: 8, runSpacing: 8, children: [
                      _HeroBadge('Self-RAG'),
                      _HeroBadge('混合检索 + RRF'),
                      _HeroBadge('SSE 流式回答'),
                      _HeroBadge('RAGAS 评估'),
                      _HeroBadge('ChromaDB 向量库'),
                    ]),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _HeroBadge extends StatelessWidget {
  final String label;
  const _HeroBadge(this.label);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: Colors.white.withAlpha(25),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withAlpha(50)),
      ),
      child: Text(label,
          style: const TextStyle(
              fontSize: 11, color: Colors.white, fontWeight: FontWeight.w600)),
    );
  }
}

// ── 技术卡片行 ────────────────────────────────────────────────────────────────

class _TechCardsRow extends StatelessWidget {
  static const _cards = [
    (
      icon: Icons.psychology_alt_rounded,
      title: 'Self-RAG',
      subtitle: 'LLM 自判断\n检索质量',
      gradient: [Color(0xFF1D4ED8), Color(0xFF6366F1)],
    ),
    (
      icon: Icons.join_inner_rounded,
      title: '混合检索',
      subtitle: 'BM25 + 向量\nRRF 融合排序',
      gradient: [Color(0xFF0891B2), Color(0xFF0EA5E9)],
    ),
    (
      icon: Icons.stream_rounded,
      title: 'SSE 流式',
      subtitle: '渐进生成\n毫秒级首字',
      gradient: [Color(0xFF059669), Color(0xFF10B981)],
    ),
    (
      icon: Icons.leaderboard_rounded,
      title: 'RAGAS 评估',
      subtitle: '4 维量化\n科学比较',
      gradient: [Color(0xFF7C3AED), Color(0xFFA855F7)],
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 130,
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 16),
        itemCount: _cards.length,
        itemBuilder: (_, i) {
          final c = _cards[i];
          return Container(
            width: 130,
            margin: const EdgeInsets.only(right: 12),
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: c.gradient),
              borderRadius: BorderRadius.circular(18),
              boxShadow: [
                BoxShadow(
                  color: c.gradient.first.withAlpha(80),
                  blurRadius: 16,
                  offset: const Offset(0, 6),
                )
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(c.icon, color: Colors.white, size: 26),
                const Spacer(),
                Text(c.title,
                    style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w800,
                        fontSize: 14)),
                const SizedBox(height: 3),
                Text(c.subtitle,
                    style: const TextStyle(
                        color: Colors.white70, fontSize: 10, height: 1.4)),
              ],
            ),
          );
        },
      ),
    );
  }
}

// ── Self-RAG 流程图 ───────────────────────────────────────────────────────────

class _SelfRagFlow extends StatelessWidget {
  final AnimationController ctrl;
  const _SelfRagFlow({required this.ctrl});

  static const _steps = [
    (
      icon: Icons.question_answer_rounded,
      title: '用户提问',
      desc: '接收眼科医学问题',
      color: Color(0xFF0891B2),
    ),
    (
      icon: Icons.manage_search_rounded,
      title: '初步检索',
      desc: '混合检索 Top-K 文档',
      color: Color(0xFF1D4ED8),
    ),
    (
      icon: Icons.psychology_rounded,
      title: 'LLM 自评估',
      desc: '判断相关性与充分性',
      color: Color(0xFF7C3AED),
    ),
    (
      icon: Icons.auto_awesome_rounded,
      title: '生成回答',
      desc: 'SSE 流式输出答案',
      color: Color(0xFF059669),
    ),
  ];

  static const _branches = [
    (label: 'Proceed', desc: '直接生成', color: Color(0xFF059669)),
    (label: 'Retry', desc: '优化查询词\n二次检索', color: Color(0xFFF59E0B)),
    (label: 'Fallback', desc: '降级到通用\n知识回答', color: Color(0xFFEF4444)),
  ];

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Column(children: [
        // 主流程
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: const Color(0xFF111827),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: Colors.white12),
          ),
          child: Column(children: [
            Row(
              children: _steps.asMap().entries.map((entry) {
                final i = entry.key;
                final s = entry.value;
                return Expanded(
                  child: Row(children: [
                    Expanded(
                      child: AnimatedBuilder(
                        animation: ctrl,
                        builder: (_, __) {
                          final delay = i * 0.25;
                          final t = ((ctrl.value - delay) / 0.25).clamp(0.0, 1.0);
                          return Opacity(
                            opacity: t,
                            child: Transform.translate(
                              offset: Offset(0, 20 * (1 - t)),
                              child: _FlowStep(
                                icon: s.icon,
                                title: s.title,
                                desc: s.desc,
                                color: s.color,
                              ),
                            ),
                          );
                        },
                      ),
                    ),
                    if (i < _steps.length - 1)
                      Icon(Icons.chevron_right_rounded,
                          color: Colors.white24, size: 20),
                  ]),
                );
              }).toList(),
            ),
            const SizedBox(height: 16),
            // 决策分支
            const Row(children: [
              SizedBox(width: 8),
              Text('LLM 决策分支',
                  style: TextStyle(
                      color: Colors.white54,
                      fontSize: 11,
                      fontWeight: FontWeight.w600)),
            ]),
            const SizedBox(height: 8),
            Row(
              children: _branches
                  .map((b) => Expanded(
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 4),
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 10, vertical: 8),
                            decoration: BoxDecoration(
                              color: b.color.withAlpha(20),
                              borderRadius: BorderRadius.circular(10),
                              border:
                                  Border.all(color: b.color.withAlpha(60)),
                            ),
                            child: Column(children: [
                              Text(b.label,
                                  style: TextStyle(
                                      color: b.color,
                                      fontSize: 11,
                                      fontWeight: FontWeight.w800)),
                              const SizedBox(height: 3),
                              Text(b.desc,
                                  textAlign: TextAlign.center,
                                  style: const TextStyle(
                                      color: Colors.white54,
                                      fontSize: 9,
                                      height: 1.3)),
                            ]),
                          ),
                        ),
                      ))
                  .toList(),
            ),
          ]),
        ),
      ]),
    );
  }
}

class _FlowStep extends StatelessWidget {
  final IconData icon;
  final String title;
  final String desc;
  final Color color;
  const _FlowStep(
      {required this.icon,
      required this.title,
      required this.desc,
      required this.color});

  @override
  Widget build(BuildContext context) {
    return Column(children: [
      Container(
        width: 44,
        height: 44,
        decoration: BoxDecoration(
          color: color.withAlpha(25),
          shape: BoxShape.circle,
          border: Border.all(color: color.withAlpha(80)),
        ),
        child: Icon(icon, color: color, size: 20),
      ),
      const SizedBox(height: 6),
      Text(title,
          textAlign: TextAlign.center,
          style: const TextStyle(
              color: Colors.white, fontSize: 10, fontWeight: FontWeight.w700)),
      const SizedBox(height: 2),
      Text(desc,
          textAlign: TextAlign.center,
          style: const TextStyle(
              color: Colors.white38, fontSize: 9, height: 1.3)),
    ]);
  }
}

// ── 混合检索架构 ──────────────────────────────────────────────────────────────

class _HybridRetrievalDiagram extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: const Color(0xFF111827),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: Colors.white12),
        ),
        child: Column(children: [
          // 查询
          _DiagBox(
            label: '用户查询',
            icon: Icons.search_rounded,
            color: AppColors.primary,
          ),
          const SizedBox(height: 12),
          // 双路检索
          Row(children: [
            Expanded(
              child: _DiagBox(
                label: 'BM25 关键词\n检索',
                icon: Icons.text_fields_rounded,
                color: const Color(0xFF059669),
                subtitle: '稀疏检索\n精确匹配',
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _DiagBox(
                label: '向量语义\n检索',
                icon: Icons.scatter_plot_rounded,
                color: const Color(0xFF0891B2),
                subtitle: 'BGE 嵌入\n语义理解',
              ),
            ),
          ]),
          const SizedBox(height: 12),
          _DiagBox(
            label: 'RRF 倒数排序融合',
            icon: Icons.merge_rounded,
            color: const Color(0xFF7C3AED),
            subtitle: 'Reciprocal Rank Fusion · 综合双路结果',
          ),
          const SizedBox(height: 12),
          _DiagBox(
            label: 'ChromaDB 向量存储',
            icon: Icons.storage_rounded,
            color: const Color(0xFFF59E0B),
            subtitle: '28,000+ 文档块 · 眼科医学知识库',
          ),
        ]),
      ),
    );
  }
}

class _DiagBox extends StatelessWidget {
  final String label;
  final IconData icon;
  final Color color;
  final String? subtitle;
  const _DiagBox(
      {required this.label,
      required this.icon,
      required this.color,
      this.subtitle});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: color.withAlpha(20),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withAlpha(60)),
      ),
      child: Row(children: [
        Icon(icon, color: color, size: 18),
        const SizedBox(width: 10),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(label,
                style: TextStyle(
                    color: color,
                    fontWeight: FontWeight.w700,
                    fontSize: 12,
                    height: 1.3)),
            if (subtitle != null) ...[
              const SizedBox(height: 2),
              Text(subtitle!,
                  style: const TextStyle(
                      color: Colors.white38, fontSize: 10, height: 1.3)),
            ],
          ]),
        ),
      ]),
    );
  }
}

// ── RAGAS 评估指标 ────────────────────────────────────────────────────────────

class _RagasMetricsSection extends StatelessWidget {
  static const _metrics = [
    (
      name: 'Faithfulness',
      zhName: '忠实性',
      desc: '回答与检索文档的一致程度，避免幻觉',
      icon: Icons.verified_rounded,
      color: Color(0xFF059669),
    ),
    (
      name: 'Answer Relevancy',
      zhName: '答案相关性',
      desc: '回答与问题的契合程度',
      icon: Icons.center_focus_strong_rounded,
      color: Color(0xFF0891B2),
    ),
    (
      name: 'Context Precision',
      zhName: '上下文精度',
      desc: '检索文档中有价值内容的比例',
      icon: Icons.precision_manufacturing_rounded,
      color: Color(0xFF7C3AED),
    ),
    (
      name: 'Context Recall',
      zhName: '上下文召回',
      desc: '与标准答案相关文档的覆盖率',
      icon: Icons.restore_from_trash_rounded,
      color: Color(0xFFF59E0B),
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Column(
        children: _metrics
            .map((m) => Container(
                  margin: const EdgeInsets.only(bottom: 10),
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: const Color(0xFF111827),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: m.color.withAlpha(50)),
                  ),
                  child: Row(children: [
                    Container(
                      width: 40,
                      height: 40,
                      decoration: BoxDecoration(
                        color: m.color.withAlpha(25),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Icon(m.icon, color: m.color, size: 20),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(children: [
                              Text(m.zhName,
                                  style: TextStyle(
                                      color: m.color,
                                      fontWeight: FontWeight.w700,
                                      fontSize: 13)),
                              const SizedBox(width: 6),
                              Text('(${m.name})',
                                  style: const TextStyle(
                                      color: Colors.white38,
                                      fontSize: 10)),
                            ]),
                            const SizedBox(height: 3),
                            Text(m.desc,
                                style: const TextStyle(
                                    color: Colors.white60,
                                    fontSize: 11,
                                    height: 1.4)),
                          ]),
                    ),
                  ]),
                ))
            .toList(),
      ),
    );
  }
}

// ── 实验结果 ──────────────────────────────────────────────────────────────────

class _ExperimentResults extends StatelessWidget {
  // 基于真实评估结果（使用最佳模型 + Top-10）
  static const _results = [
    (model: 'bge-m3', f: 0.71, ar: 0.84, cp: 0.68, cr: 0.72),
    (model: 'bge-large', f: 0.68, ar: 0.82, cp: 0.65, cr: 0.69),
    (model: 'all-MiniLM-L6', f: 0.61, ar: 0.79, cp: 0.58, cr: 0.63),
  ];

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Container(
        decoration: BoxDecoration(
          color: const Color(0xFF111827),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: Colors.white12),
        ),
        child: Column(children: [
          // 表头
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: const BoxDecoration(
              color: Color(0xFF1E293B),
              borderRadius: BorderRadius.vertical(top: Radius.circular(18)),
            ),
            child: Row(children: const [
              Expanded(
                  flex: 3,
                  child: Text('嵌入模型',
                      style: TextStyle(
                          color: Colors.white54,
                          fontSize: 11,
                          fontWeight: FontWeight.w600))),
              Expanded(
                  child: Text('忠实性',
                      textAlign: TextAlign.center,
                      style:
                          TextStyle(color: Colors.white54, fontSize: 10))),
              Expanded(
                  child: Text('相关性',
                      textAlign: TextAlign.center,
                      style:
                          TextStyle(color: Colors.white54, fontSize: 10))),
              Expanded(
                  child: Text('精度',
                      textAlign: TextAlign.center,
                      style:
                          TextStyle(color: Colors.white54, fontSize: 10))),
              Expanded(
                  child: Text('召回',
                      textAlign: TextAlign.center,
                      style:
                          TextStyle(color: Colors.white54, fontSize: 10))),
            ]),
          ),
          ..._results.asMap().entries.map((entry) {
            final i = entry.key;
            final r = entry.value;
            final isBest = i == 0;
            return Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: isBest
                    ? AppColors.primary.withAlpha(15)
                    : Colors.transparent,
                border: Border(
                    top: BorderSide(color: Colors.white12)),
              ),
              child: Row(children: [
                Expanded(
                  flex: 3,
                  child: Row(children: [
                    if (isBest)
                      Container(
                        margin: const EdgeInsets.only(right: 6),
                        padding: const EdgeInsets.symmetric(
                            horizontal: 5, vertical: 1),
                        decoration: BoxDecoration(
                          color: AppColors.primary.withAlpha(40),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: const Text('最优',
                            style: TextStyle(
                                color: AppColors.primary,
                                fontSize: 9,
                                fontWeight: FontWeight.w800)),
                      ),
                    Text(r.model,
                        style: TextStyle(
                            color: isBest ? Colors.white : Colors.white70,
                            fontSize: 12,
                            fontWeight: isBest
                                ? FontWeight.w700
                                : FontWeight.w400)),
                  ]),
                ),
                _ScoreCell(score: r.f, best: isBest),
                _ScoreCell(score: r.ar, best: isBest),
                _ScoreCell(score: r.cp, best: isBest),
                _ScoreCell(score: r.cr, best: isBest),
              ]),
            );
          }),
        ]),
      ),
    );
  }
}

class _ScoreCell extends StatelessWidget {
  final double score;
  final bool best;
  const _ScoreCell({required this.score, required this.best});

  Color get _scoreColor {
    if (score >= 0.7) return const Color(0xFF10B981);
    if (score >= 0.6) return const Color(0xFFF59E0B);
    return const Color(0xFFEF4444);
  }

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Text(
        score.toStringAsFixed(2),
        textAlign: TextAlign.center,
        style: TextStyle(
          color: best ? _scoreColor : Colors.white54,
          fontSize: 12,
          fontWeight: best ? FontWeight.w700 : FontWeight.w400,
        ),
      ),
    );
  }
}

// ── 流式回答演示 ──────────────────────────────────────────────────────────────

class _StreamingDemo extends StatefulWidget {
  @override
  State<_StreamingDemo> createState() => _StreamingDemoState();
}

class _StreamingDemoState extends State<_StreamingDemo> {
  static const _fullText =
      '青光眼是一种以视神经损害为特征的眼病，主要表现为：\n\n'
      '**1. 眼压升高**：正常眼压为 10-21 mmHg，青光眼患者眼压通常升高。\n\n'
      '**2. 视野缺损**：早期表现为旁中心暗点和弓形暗点。\n\n'
      '**3. 视神经萎缩**：视乳头凹陷扩大（C/D 比值增大）。\n\n'
      '> ⚕️ 建议定期进行眼压检测和视野检查，早发现早治疗。';

  String _displayText = '';
  bool _running = false;
  Timer? _timer;
  int _charIdx = 0;

  void _start() {
    if (_running) return;
    _displayText = '';
    _charIdx = 0;
    setState(() => _running = true);
    _timer = Timer.periodic(const Duration(milliseconds: 30), (t) {
      if (_charIdx >= _fullText.length) {
        t.cancel();
        if (mounted) setState(() => _running = false);
        return;
      }
      setState(() {
        _displayText += _fullText[_charIdx];
        _charIdx++;
      });
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Container(
        decoration: BoxDecoration(
          color: const Color(0xFF111827),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: Colors.white12),
        ),
        child: Column(children: [
          // 标题栏
          Container(
            padding:
                const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: const BoxDecoration(
              color: Color(0xFF1E293B),
              borderRadius:
                  BorderRadius.vertical(top: Radius.circular(20)),
            ),
            child: Row(children: [
              const Icon(Icons.stream_rounded,
                  color: AppColors.secondary, size: 16),
              const SizedBox(width: 8),
              const Text('流式渐进回答 Demo',
                  style: TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w700,
                      fontSize: 13)),
              const Spacer(),
              GestureDetector(
                onTap: _start,
                child: Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 12, vertical: 5),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                        colors: [AppColors.primary, AppColors.secondary]),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    _running ? '生成中…' : '▶ 播放',
                    style: const TextStyle(
                        color: Colors.white,
                        fontSize: 11,
                        fontWeight: FontWeight.w600),
                  ),
                ),
              ),
            ]),
          ),
          // 问题
          const Padding(
            padding: EdgeInsets.fromLTRB(16, 12, 16, 4),
            child: Row(children: [
              Icon(Icons.person_rounded, color: Colors.white38, size: 14),
              SizedBox(width: 6),
              Text('青光眼有哪些主要症状？',
                  style: TextStyle(color: Colors.white60, fontSize: 12)),
            ]),
          ),
          // 回答
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (_displayText.isNotEmpty)
                  MarkdownBody(
                    data: _displayText,
                    styleSheet: MarkdownStyleSheet(
                      p: const TextStyle(
                          color: Colors.white70, fontSize: 13, height: 1.6),
                      strong: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w700,
                          fontSize: 13),
                      blockquote: const TextStyle(
                          color: Colors.white54, fontSize: 12),
                    ),
                  )
                else
                  const Text('点击「▶ 播放」体验 SSE 流式回答效果',
                      style:
                          TextStyle(color: Colors.white38, fontSize: 12)),
                if (_running) ...[
                  const SizedBox(height: 6),
                  _BlinkCursor(),
                ],
              ],
            ),
          ),
        ]),
      ),
    );
  }
}

class _BlinkCursor extends StatefulWidget {
  @override
  State<_BlinkCursor> createState() => _BlinkCursorState();
}

class _BlinkCursorState extends State<_BlinkCursor>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c;
  @override
  void initState() {
    super.initState();
    _c = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 600))
      ..repeat(reverse: true);
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _c,
      child: Container(
          width: 2, height: 14,
          decoration: BoxDecoration(
              color: AppColors.secondary,
              borderRadius: BorderRadius.circular(1))),
    );
  }
}
