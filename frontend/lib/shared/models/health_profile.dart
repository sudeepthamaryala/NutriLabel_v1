// lib/shared/models/health_profile.dart

enum Sex { male, female, other }

enum ActivityLevel { sedentary, light, moderate, active, very_active }

enum HealthGoal { weight_loss, weight_maintenance, weight_gain, muscle_gain }

extension SexLabel on Sex {
  String get label {
    switch (this) {
      case Sex.male: return 'Male';
      case Sex.female: return 'Female';
      case Sex.other: return 'Other';
    }
  }
  String get value => name;
}

extension ActivityLevelLabel on ActivityLevel {
  String get label {
    switch (this) {
      case ActivityLevel.sedentary: return 'Sedentary';
      case ActivityLevel.light: return 'Lightly Active';
      case ActivityLevel.moderate: return 'Moderately Active';
      case ActivityLevel.active: return 'Active';
      case ActivityLevel.very_active: return 'Very Active';
    }
  }
  String get value => name;
}

extension HealthGoalLabel on HealthGoal {
  String get label {
    switch (this) {
      case HealthGoal.weight_loss: return 'Lose Weight';
      case HealthGoal.weight_maintenance: return 'Maintain Weight';
      case HealthGoal.weight_gain: return 'Gain Weight';
      case HealthGoal.muscle_gain: return 'Build Muscle';
    }
  }
  String get value => name;
}

class HealthProfile {
  final String? id;
  final String? userId;
  final int age;
  final double weightKg;
  final double heightCm;
  final Sex sex;
  final ActivityLevel activityLevel;
  final HealthGoal goal;
  final List<String> allergies;
  final List<String> diseases;
  final List<String> dietaryPreferences;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  const HealthProfile({
    this.id,
    this.userId,
    required this.age,
    required this.weightKg,
    required this.heightCm,
    required this.sex,
    required this.activityLevel,
    required this.goal,
    this.allergies = const [],
    this.diseases = const [],
    this.dietaryPreferences = const [],
    this.createdAt,
    this.updatedAt,
  });

  factory HealthProfile.fromJson(Map<String, dynamic> json) => HealthProfile(
        id: json['id'] as String?,
        userId: json['user_id'] as String?,
        age: (json['age'] as num).toInt(),
        weightKg: double.parse(json['weight_kg'].toString()),
        heightCm: double.parse(json['height_cm'].toString()),
        sex: Sex.values.firstWhere((e) => e.name == json['sex']),
        activityLevel: ActivityLevel.values
            .firstWhere((e) => e.name == json['activity_level']),
        goal: HealthGoal.values.firstWhere((e) => e.name == json['goal']),
        allergies: List<String>.from(json['allergies'] ?? []),
        diseases: List<String>.from(json['diseases'] ?? []),
        dietaryPreferences:
            List<String>.from(json['dietary_preferences'] ?? []),
        createdAt: json['created_at'] != null
            ? DateTime.parse(json['created_at'] as String)
            : null,
        updatedAt: json['updated_at'] != null
            ? DateTime.parse(json['updated_at'] as String)
            : null,
      );

  Map<String, dynamic> toJson() => {
        'age': age,
        'weight_kg': weightKg.toStringAsFixed(2),
        'height_cm': heightCm.toStringAsFixed(2),
        'sex': sex.value,
        'activity_level': activityLevel.value,
        'goal': goal.value,
        'allergies': allergies,
        'diseases': diseases,
        'dietary_preferences': dietaryPreferences,
      };

  HealthProfile copyWith({
    String? id,
    String? userId,
    int? age,
    double? weightKg,
    double? heightCm,
    Sex? sex,
    ActivityLevel? activityLevel,
    HealthGoal? goal,
    List<String>? allergies,
    List<String>? diseases,
    List<String>? dietaryPreferences,
  }) =>
      HealthProfile(
        id: id ?? this.id,
        userId: userId ?? this.userId,
        age: age ?? this.age,
        weightKg: weightKg ?? this.weightKg,
        heightCm: heightCm ?? this.heightCm,
        sex: sex ?? this.sex,
        activityLevel: activityLevel ?? this.activityLevel,
        goal: goal ?? this.goal,
        allergies: allergies ?? this.allergies,
        diseases: diseases ?? this.diseases,
        dietaryPreferences: dietaryPreferences ?? this.dietaryPreferences,
        createdAt: createdAt,
        updatedAt: updatedAt,
      );
}
