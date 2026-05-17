import 'dart:convert';
import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:file_saver/file_saver.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

const apiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://localhost:8000',
);

void main() {
  runApp(const Tp100App());
}

class Tp100App extends StatelessWidget {
  const Tp100App({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ТП-100 Диагностика',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF2563EB)),
        appBarTheme: const AppBarTheme(
          scrolledUnderElevation: 0,
          surfaceTintColor: Colors.transparent,
        ),
        useMaterial3: true,
      ),
      home: const DiagnosticsPage(),
    );
  }
}

class DiagnosticsPage extends StatefulWidget {
  const DiagnosticsPage({super.key});

  @override
  State<DiagnosticsPage> createState() => _DiagnosticsPageState();
}

class _DiagnosticsPageState extends State<DiagnosticsPage> {
  PlatformFile? _selectedFile;
  UploadResult? _uploadResult;
  AnalysisResult? _analysisResult;
  bool _isUploading = false;
  bool _isAnalyzing = false;
  String? _error;

  Future<void> _pickFile() async {
    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['csv'],
        withData: true,
      );
      if (result == null || result.files.isEmpty) return;
      setState(() {
        _selectedFile = result.files.first;
        _uploadResult = null;
        _analysisResult = null;
        _error = null;
      });
    } catch (error) {
      setState(() => _error = 'Не удалось открыть окно выбора файла: $error');
    }
  }

  Future<void> _uploadFile() async {
    final file = _selectedFile;
    final bytes = file?.bytes;
    if (file == null || bytes == null) {
      setState(() => _error = 'Выберите CSV-файл перед отправкой.');
      return;
    }

    setState(() {
      _isUploading = true;
      _error = null;
      _analysisResult = null;
    });

    try {
      final request = http.MultipartRequest('POST', Uri.parse('$apiBaseUrl/api/upload'));
      request.files.add(http.MultipartFile.fromBytes('file', bytes, filename: file.name));
      final streamed = await request.send();
      final response = await http.Response.fromStream(streamed);
      if (response.statusCode >= 400) {
        throw Exception(_extractError(response.body));
      }
      setState(() {
        _uploadResult = UploadResult.fromJson(jsonDecode(utf8.decode(response.bodyBytes)));
      });
    } catch (error) {
      setState(() => _error = 'Не удалось отправить данные: $error');
    } finally {
      setState(() => _isUploading = false);
    }
  }

  Future<void> _analyze() async {
    final sessionId = _uploadResult?.sessionId;
    if (sessionId == null) return;

    setState(() {
      _isAnalyzing = true;
      _error = null;
    });

    try {
      final response = await http.post(Uri.parse('$apiBaseUrl/api/analyze/$sessionId'));
      if (response.statusCode >= 400) {
        throw Exception(_extractError(response.body));
      }
      setState(() {
        _analysisResult = AnalysisResult.fromJson(jsonDecode(utf8.decode(response.bodyBytes)));
      });
    } catch (error) {
      setState(() => _error = 'Не удалось выполнить анализ: $error');
    } finally {
      setState(() => _isAnalyzing = false);
    }
  }

  void _reset() {
    setState(() {
      _selectedFile = null;
      _uploadResult = null;
      _analysisResult = null;
      _error = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    final result = _uploadResult;
    final analysis = _analysisResult;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Диагностика котла ТП-100'),
        actions: [
          if ((_selectedFile != null || result != null) && analysis == null)
            IconButton(
              tooltip: 'Анализировать другой файл',
              onPressed: _reset,
              icon: const Icon(Icons.refresh),
            ),
        ],
      ),
      bottomNavigationBar: analysis == null
          ? null
          : SafeArea(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
                child: Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  alignment: WrapAlignment.end,
                  children: [
                    OutlinedButton.icon(
                      onPressed: () => _downloadReport(analysis),
                      icon: const Icon(Icons.download),
                      label: const Text('Скачать отчёт'),
                    ),
                    FilledButton.icon(
                      onPressed: _reset,
                      icon: const Icon(Icons.refresh),
                      label: const Text('Анализировать другой файл'),
                    ),
                  ],
                ),
              ),
            ),
      body: SafeArea(
        child: AnimatedSwitcher(
          duration: const Duration(milliseconds: 220),
          child: analysis != null
              ? ReportView(analysis: analysis)
              : _isAnalyzing
                  ? const LoadingView(message: 'Данные анализируются, формируется отчет...')
                  : SingleChildScrollView(
                      padding: const EdgeInsets.all(24),
                      child: Center(
                        child: ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 1100),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              UploadPanel(
                                selectedFile: _selectedFile,
                                isUploading: _isUploading,
                                onPickFile: _pickFile,
                                onUpload: _uploadFile,
                              ),
                              if (_error != null) ...[
                                const SizedBox(height: 16),
                                ErrorBanner(message: _error!),
                              ],
                              if (result != null) ...[
                                const SizedBox(height: 24),
                                ChartsView(result: result),
                                const SizedBox(height: 20),
                                FilledButton.icon(
                                  onPressed: _analyze,
                                  icon: const Icon(Icons.analytics_outlined),
                                  label: const Text('Анализировать данные'),
                                ),
                              ],
                            ],
                          ),
                        ),
                      ),
                    ),
        ),
      ),
    );
  }

  Future<void> _downloadReport(AnalysisResult analysis) async {
    final bytes = Uint8List.fromList(utf8.encode(analysis.report));
    final timestamp = DateTime.now().toIso8601String().replaceAll(':', '-').split('.').first;
    await FileSaver.instance.saveFile(
      name: 'tp100_report_$timestamp',
      bytes: bytes,
      ext: 'txt',
      mimeType: MimeType.text,
    );
  }
}

class UploadPanel extends StatelessWidget {
  const UploadPanel({
    required this.selectedFile,
    required this.isUploading,
    required this.onPickFile,
    required this.onUpload,
    super.key,
  });

  final PlatformFile? selectedFile;
  final bool isUploading;
  final VoidCallback onPickFile;
  final VoidCallback onUpload;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Загрузка диагностических данных', style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 14),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                OutlinedButton.icon(
                  onPressed: isUploading ? null : onPickFile,
                  icon: const Icon(Icons.upload_file),
                  label: const Text('Выбрать CSV'),
                ),
                FilledButton.icon(
                  onPressed: isUploading ? null : onUpload,
                  icon: isUploading
                      ? const SizedBox.square(
                          dimension: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.cloud_upload_outlined),
                  label: Text(isUploading ? 'Отправка...' : 'Отправить данные на сервер'),
                ),
              ],
            ),
            if (selectedFile != null) ...[
              const SizedBox(height: 14),
              Text('Выбран файл: ${selectedFile!.name}'),
            ],
          ],
        ),
      ),
    );
  }
}

class ChartsView extends StatelessWidget {
  const ChartsView({required this.result, super.key});

  final UploadResult result;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Обработано строк: ${result.rows}. Построено графиков: ${result.charts.length}.',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 12),
        LayoutBuilder(
          builder: (context, constraints) {
            final isWide = constraints.maxWidth > 760;
            return GridView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: isWide ? 2 : 1,
                mainAxisSpacing: 16,
                crossAxisSpacing: 16,
                childAspectRatio: 1.75,
              ),
              itemCount: result.charts.length,
              itemBuilder: (context, index) {
                final chart = result.charts[index];
                return DecoratedBox(
                  decoration: BoxDecoration(
                    border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Padding(
                        padding: const EdgeInsets.fromLTRB(12, 10, 12, 6),
                        child: Text(
                          chart.parameter,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: Theme.of(context).textTheme.titleSmall,
                        ),
                      ),
                      Expanded(
                        child: Image.network(
                          '$apiBaseUrl${chart.url}',
                          fit: BoxFit.contain,
                          errorBuilder: (context, error, stackTrace) => const Center(child: Text('График недоступен')),
                        ),
                      ),
                    ],
                  ),
                );
              },
            );
          },
        ),
      ],
    );
  }
}

class ReportView extends StatelessWidget {
  const ReportView({required this.analysis, super.key});

  final AnalysisResult analysis;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1000),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text('Результаты анализа', style: Theme.of(context).textTheme.headlineSmall),
              const SizedBox(height: 16),
              ClassificationSummary(items: analysis.checkedParameters),
              const SizedBox(height: 20),
              DecoratedBox(
                decoration: BoxDecoration(
                  border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: SelectableText(
                    analysis.report,
                    style: Theme.of(context).textTheme.bodyLarge?.copyWith(height: 1.45),
                  ),
                ),
              ),
              const SizedBox(height: 72),
            ],
          ),
        ),
      ),
    );
  }
}

class ClassificationSummary extends StatelessWidget {
  const ClassificationSummary({required this.items, super.key});

  final List<ParameterClassification> items;

  @override
  Widget build(BuildContext context) {
    final grouped = <String, List<ParameterClassification>>{
      'нормальное': [],
      'предаварийное': [],
      'аварийное': [],
      'нет данных': [],
    };
    for (final item in items) {
      grouped.putIfAbsent(item.status, () => []).add(item);
    }

    return Wrap(
      spacing: 12,
      runSpacing: 12,
      children: grouped.entries.map((entry) {
        return SizedBox(
          width: 230,
          child: DecoratedBox(
            decoration: BoxDecoration(
              border: Border.all(color: _statusColor(entry.key).withValues(alpha: 0.45)),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(entry.key, style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  Text('${entry.value.length} параметров'),
                ],
              ),
            ),
          ),
        );
      }).toList(),
    );
  }

  Color _statusColor(String status) {
    return switch (status) {
      'аварийное' => const Color(0xFFDC2626),
      'предаварийное' => const Color(0xFFD97706),
      'нормальное' => const Color(0xFF16A34A),
      _ => const Color(0xFF64748B),
    };
  }
}

class LoadingView extends StatelessWidget {
  const LoadingView({required this.message, super.key});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const CircularProgressIndicator(),
          const SizedBox(height: 18),
          Text(message),
        ],
      ),
    );
  }
}

class ErrorBanner extends StatelessWidget {
  const ErrorBanner({required this.message, super.key});

  final String message;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.errorContainer,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Text(
          message,
          style: TextStyle(color: Theme.of(context).colorScheme.onErrorContainer),
        ),
      ),
    );
  }
}

class UploadResult {
  UploadResult({
    required this.sessionId,
    required this.rows,
    required this.parameters,
    required this.charts,
  });

  final String sessionId;
  final int rows;
  final List<String> parameters;
  final List<ChartInfo> charts;

  factory UploadResult.fromJson(Map<String, dynamic> json) {
    return UploadResult(
      sessionId: json['session_id'] as String,
      rows: json['rows'] as int,
      parameters: (json['parameters'] as List<dynamic>).cast<String>(),
      charts: (json['charts'] as List<dynamic>)
          .map((item) => ChartInfo.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }
}

class ChartInfo {
  ChartInfo({required this.name, required this.parameter, required this.url});

  final String name;
  final String parameter;
  final String url;

  factory ChartInfo.fromJson(Map<String, dynamic> json) {
    return ChartInfo(
      name: json['name'] as String,
      parameter: json['parameter'] as String,
      url: json['url'] as String,
    );
  }
}

class AnalysisResult {
  AnalysisResult({required this.checkedParameters, required this.report});

  final List<ParameterClassification> checkedParameters;
  final String report;

  factory AnalysisResult.fromJson(Map<String, dynamic> json) {
    return AnalysisResult(
      checkedParameters: (json['checked_parameters'] as List<dynamic>)
          .map((item) => ParameterClassification.fromJson(item as Map<String, dynamic>))
          .toList(),
      report: json['report'] as String,
    );
  }
}

class ParameterClassification {
  ParameterClassification({required this.parameter, required this.status});

  final String parameter;
  final String status;

  factory ParameterClassification.fromJson(Map<String, dynamic> json) {
    return ParameterClassification(
      parameter: json['parameter'] as String,
      status: json['status'] as String,
    );
  }
}

String _extractError(String body) {
  try {
    final decoded = jsonDecode(body) as Map<String, dynamic>;
    return decoded['detail']?.toString() ?? body;
  } catch (_) {
    return body;
  }
}
