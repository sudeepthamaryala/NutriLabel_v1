// lib/shared/models/chat.dart

enum ChatSessionType { analyse, compare }

enum ChatRole { user, assistant }

class NutritionData {
  final double? calories;
  final double? fatG;
  final double? proteinG;
  final double? sugarG;
  final double? sodiumMg;
  final String? servingSize;
  final List<String> ingredients;

  const NutritionData({
    this.calories,
    this.fatG,
    this.proteinG,
    this.sugarG,
    this.sodiumMg,
    this.servingSize,
    this.ingredients = const [],
  });

  factory NutritionData.fromJson(Map<String, dynamic> json) => NutritionData(
        calories: (json['calories'] as num?)?.toDouble(),
        fatG: (json['fat_g'] as num?)?.toDouble(),
        proteinG: (json['protein_g'] as num?)?.toDouble(),
        sugarG: (json['sugar_g'] as num?)?.toDouble(),
        sodiumMg: (json['sodium_mg'] as num?)?.toDouble(),
        servingSize: json['serving_size'] as String?,
        ingredients: List<String>.from(json['ingredients'] ?? []),
      );
}

class AnalyseAnswer {
  final String summary;
  final List<String> recommendations;
  final List<String> warnings;

  const AnalyseAnswer({
    required this.summary,
    this.recommendations = const [],
    this.warnings = const [],
  });

  factory AnalyseAnswer.fromJson(Map<String, dynamic> json) => AnalyseAnswer(
        summary: json['summary'] as String,
        recommendations: List<String>.from(json['recommendations'] ?? []),
        warnings: List<String>.from(json['warnings'] ?? []),
      );
}

class AnalyseResult {
  final String sessionId;
  final NutritionData nutrition;
  final AnalyseAnswer answer;
  final double confidence;

  const AnalyseResult({
    required this.sessionId,
    required this.nutrition,
    required this.answer,
    required this.confidence,
  });

  factory AnalyseResult.fromJson(Map<String, dynamic> json) => AnalyseResult(
        sessionId: json['session_id'] as String,
        nutrition: NutritionData.fromJson(
            json['nutrition'] as Map<String, dynamic>),
        answer:
            AnalyseAnswer.fromJson(json['answer'] as Map<String, dynamic>),
        confidence: (json['confidence'] as num).toDouble(),
      );
}

class ComparedProduct {
  final int index;
  final NutritionData nutrition;

  const ComparedProduct({required this.index, required this.nutrition});

  factory ComparedProduct.fromJson(Map<String, dynamic> json) =>
      ComparedProduct(
        index: json['index'] as int,
        nutrition: NutritionData.fromJson(
            json['nutrition'] as Map<String, dynamic>),
      );
}

class CompareVerdict {
  final String bestProduct;
  final List<String> reasons;
  final List<String> tradeoffs;
  final List<String> warnings;

  const CompareVerdict({
    required this.bestProduct,
    this.reasons = const [],
    this.tradeoffs = const [],
    this.warnings = const [],
  });

  factory CompareVerdict.fromJson(Map<String, dynamic> json) => CompareVerdict(
        bestProduct: json['best_product'] as String,
        reasons: List<String>.from(json['reasons'] ?? []),
        tradeoffs: List<String>.from(json['tradeoffs'] ?? []),
        warnings: List<String>.from(json['warnings'] ?? []),
      );
}

class CompareResult {
  final String sessionId;
  final List<ComparedProduct> products;
  final int bestProductIndex;
  final CompareVerdict verdict;

  const CompareResult({
    required this.sessionId,
    required this.products,
    required this.bestProductIndex,
    required this.verdict,
  });

  factory CompareResult.fromJson(Map<String, dynamic> json) => CompareResult(
        sessionId: json['session_id'] as String,
        products: (json['products'] as List)
            .map((p) => ComparedProduct.fromJson(p as Map<String, dynamic>))
            .toList(),
        bestProductIndex: json['best_product_index'] as int,
        verdict: CompareVerdict.fromJson(
            json['verdict'] as Map<String, dynamic>),
      );
}

class ChatSession {
  final String id;
  final String userId;
  final ChatSessionType type;
  final String title;
  final DateTime createdAt;
  final DateTime updatedAt;

  const ChatSession({
    required this.id,
    required this.userId,
    required this.type,
    required this.title,
    required this.createdAt,
    required this.updatedAt,
  });

  factory ChatSession.fromJson(Map<String, dynamic> json) => ChatSession(
        id: json['id'] as String,
        userId: json['user_id'] as String,
        type: ChatSessionType.values
            .firstWhere((e) => e.name == json['type']),
        title: json['title'] as String,
        createdAt: DateTime.parse(json['created_at'] as String),
        updatedAt: DateTime.parse(json['updated_at'] as String),
      );
}
