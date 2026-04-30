import 'package:flutter/material.dart';
import 'package:package_info_plus/package_info_plus.dart';

class AboutPage extends StatelessWidget {
  const AboutPage({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('关于')),
      body: FutureBuilder<PackageInfo>(
        future: PackageInfo.fromPlatform(),
        builder: (_, snap) {
          final info = snap.data;
          return ListView(
            padding: const EdgeInsets.all(24),
            children: [
              Center(
                child: Column(
                  children: [
                    Container(
                      width: 80,
                      height: 80,
                      decoration: BoxDecoration(
                        color: theme.colorScheme.primaryContainer,
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Icon(Icons.visibility,
                          size: 48, color: theme.colorScheme.primary),
                    ),
                    const SizedBox(height: 16),
                    Text('眼科智能问答',
                        style: theme.textTheme.headlineSmall
                            ?.copyWith(fontWeight: FontWeight.bold)),
                    if (info != null)
                      Text('v${info.version} (${info.buildNumber})',
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: theme.colorScheme.onSurfaceVariant,
                          )),
                  ],
                ),
              ),
              const SizedBox(height: 32),
              _InfoCard(
                title: '项目介绍',
                content: '基于检索增强生成（RAG）技术的眼科医疗知识问答系统，整合 PubMed Central 开放获取眼科文献构建知识库，支持中文智能问答。',
              ),
              const SizedBox(height: 12),
              _InfoCard(
                title: '技术栈',
                content: '后端: FastAPI + ChromaDB + MiniMax LLM\n'
                    '嵌入模型: BGE-M3（多语言，1024维）\n'
                    '检索策略: 混合检索 + 重排序 + 双语翻译\n'
                    '移动端: Flutter（iOS / Android / Web）',
              ),
              const SizedBox(height: 12),
              _InfoCard(
                title: '作者',
                content: '鞠明轩\n云南大学软件学院\n软件工程 2022 级\n毕业设计作品（2026）',
              ),
            ],
          );
        },
      ),
    );
  }
}

class _InfoCard extends StatelessWidget {
  final String title;
  final String content;
  const _InfoCard({required this.title, required this.content});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title,
                style: theme.textTheme.titleSmall
                    ?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Text(content,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                  height: 1.6,
                )),
          ],
        ),
      ),
    );
  }
}
